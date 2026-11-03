"""RFC-5 round trips with ngff-zarr alone, on synthetic images: no registration engine, no download.

The moving image is the fixed one shifted by SHIFT voxels along x. The transformation from fixed to moving is then a
translation of SHIFT voxels, written once as an ``affine`` and once as a constant ``displacements`` field, in 3-D and
in 2-D. Each is written in a scene, read back, checked as metadata, and checked as numbers: points, the image, labels.
"""

import json
import sys
import zipfile
from pathlib import Path

import dask.array as da
import ngff_zarr as nz
import numpy as np
import pytest
from ngff_zarr import CoordinateSystemIdentifier, NgffScene
from ngff_zarr.transform_points import transform_points
from ngff_zarr.v06.zarr_metadata import Affine, Displacements

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "steps"))
from common import FIELD, scene_fields  # noqa: E402

SHIFT = 3  # voxels along x, of 1 micrometer each
SPACING = {"z": 2.0, "y": 1.0, "x": 1.0}
SHAPE = {"z": 6, "y": 24, "x": 32}


def _image(values, dims):
    image = nz.NgffImage(
        data=values,
        dims=list(dims),
        scale={d: SPACING[d] for d in dims},
        translation={d: 0.0 for d in dims},
        axes_units={d: "micrometer" for d in dims},
    )
    return nz.to_multiscales(image, scale_factors=[2])


def _pair(dims):
    """Fixed, moving (fixed shifted by SHIFT along x), and their labels, as multiscales."""
    grids = np.meshgrid(*(np.arange(SHAPE[d], dtype=float) for d in dims), indexing="ij")
    fixed = (100 + 80 * np.sin(grids[-1] / 3) * np.cos(grids[-2] / 4) + 10 * grids[0]).astype(np.float32)
    labels = ((fixed > 110) * (1 + grids[-1] // 8)).astype(np.uint16)
    return (
        _image(fixed, dims),
        _image(np.roll(fixed, SHIFT, axis=-1), dims),
        _image(labels, dims),
        _image(np.roll(labels, SHIFT, axis=-1), dims),
    )


def _write_scene(tmp_path, dims, kind):
    """A scene holding the pair and the transformation, as a store and as a .ozx; returns both paths."""
    fixed, moving, _, _ = _pair(dims)
    store, ozx = tmp_path / "pair.ome.zarr", tmp_path / "pair.ozx"
    ends = {
        "input": CoordinateSystemIdentifier(path="fixed", name="intrinsic"),
        "output": CoordinateSystemIdentifier(path="moving", name="intrinsic"),
    }
    if kind == "affine":
        matrix = np.hstack([np.eye(len(dims)), np.zeros((len(dims), 1))])
        matrix[-1, -1] = SHIFT * SPACING["x"]
        transformation = Affine(affine=matrix.tolist(), **ends)
    else:
        # The field: one vector per voxel of the fixed image, the x component SHIFT micrometers, the others 0.
        vectors = np.zeros((len(dims), *(SHAPE[d] for d in dims)), dtype=np.float32)
        vectors[-1] = SHIFT * SPACING["x"]
        field = nz.NgffImage(
            data=vectors,
            dims=["d", *dims],
            scale={"d": 1.0, **{d: SPACING[d] for d in dims}},
            translation={"d": 0.0, **{d: 0.0 for d in dims}},
            axes_units={d: "micrometer" for d in dims},
            axes_types={"d": "displacement"},
        )
        nz.to_ome_zarr(store / FIELD, nz.to_multiscales(field, scale_factors=[]), version="0.6")
        transformation = Displacements(path=FIELD, interpolation="linear", **ends)
    NgffScene(images={"fixed": fixed, "moving": moving}, coordinateTransformations=[transformation]).to_ome_zarr(
        store, overwrite=False
    )
    nz.write_store_to_zip(store, ozx, version="0.6")
    return store, ozx


@pytest.mark.parametrize("dims", ["zyx", "yx"])
@pytest.mark.parametrize("kind", ["affine", "displacements"])
@pytest.mark.parametrize("container", ["store", "ozx"])
def test_a_scene_round_trips_and_maps_points_and_images(tmp_path, dims, kind, container):
    store, ozx = _write_scene(tmp_path, dims, kind)
    scene_path = store if container == "store" else ozx

    # Metadata: the scene validates, names what it connects, and the images keep their geometry.
    scene = NgffScene.from_ome_zarr(scene_path, validate=True)
    transformation = scene.coordinateTransformations[0]
    assert transformation.type == kind
    assert (transformation.input.path, transformation.input.name) == ("fixed", "intrinsic")
    assert (transformation.output.path, transformation.output.name) == ("moving", "intrinsic")
    fixed, moving = scene.images["fixed"].images[0], scene.images["moving"].images[0]
    assert fixed.dims == list(dims) and len(scene.images["fixed"].images) == 2
    assert fixed.scale == {d: SPACING[d] for d in dims} and fixed.axes_units == {d: "micrometer" for d in dims}
    root = json.loads(
        (zipfile.ZipFile(ozx).read("zarr.json") if container == "ozx" else (store / "zarr.json").read_bytes())
    )
    assert root["attributes"]["ome"]["scene"]["coordinateTransformations"][0]["type"] == kind

    # Numbers: a point moves by SHIFT micrometers along x and nothing else, from fixed to moving.
    fields = scene_fields(scene_path, transformation)
    assert (fields is not None) == (kind == "displacements")
    points = np.array([[1.0, 2.0, 3.0][-len(dims) :], [4.0, 10.0, 20.0][-len(dims) :]])
    expected = points + np.array([0.0, 0.0, SHIFT * SPACING["x"]][-len(dims) :])
    np.testing.assert_allclose(transform_points(transformation, points, list(dims), fields=fields), expected, atol=1e-6)

    # The moving image, resampled onto the fixed grid, is the fixed image again; the result stays lazy until asked.
    moved = nz.resample(transformation, fixed, moving, fields=fields)
    assert isinstance(moved.data, da.Array)
    inside = (..., slice(0, SHAPE["x"] - SHIFT))
    np.testing.assert_allclose(np.asarray(moved.data)[inside], np.asarray(fixed.data)[inside], atol=1e-3)

    # Labels go through the same transformation with their values kept.
    _, _, labels_fixed, labels_moving = _pair(dims)
    carried = nz.resample(transformation, fixed, labels_moving.images[0], interpolator="label_image", fields=fields)
    np.testing.assert_array_equal(np.asarray(carried.data)[inside], np.asarray(labels_fixed.images[0].data)[inside])


def test_the_affine_and_its_constant_field_agree(tmp_path):
    mapped = {}
    for kind in ("affine", "displacements"):
        store, _ = _write_scene(tmp_path / kind, "zyx", kind)
        scene = NgffScene.from_ome_zarr(store)
        transformation = scene.coordinateTransformations[0]
        mapped[kind] = transform_points(
            transformation, [[1.0, 5.0, 7.0]], ["z", "y", "x"], fields=scene_fields(store, transformation)
        )
    np.testing.assert_allclose(mapped["affine"], mapped["displacements"], atol=1e-6)


def test_the_interoperability_fixture_maps_its_points(fixture=Path(__file__).parent / "fixture"):
    """Another reader checks itself the same way: open the scene, take the affine, map the points, compare."""
    case = json.loads((fixture / "points.json").read_text(encoding="utf-8"))
    scene = NgffScene.from_ome_zarr(fixture / "organoid_affine.ozx", validate=True)
    transformation = scene.coordinateTransformations[0]
    assert (
        transformation.type == "affine"
        and transformation.input.path == "fixed"
        and transformation.output.path == "moving"
    )
    assert np.asarray(transformation.affine).shape == (3, 4)
    # ngff-zarr's answer, and the matrix applied by hand: both within the fixture's tolerance of the expected points.
    matrix = np.asarray(transformation.affine)
    by_hand = np.asarray(case["points"]) @ matrix[:, :3].T + matrix[:, 3]
    np.testing.assert_allclose(by_hand, case["expected"], atol=case["tolerance"])
    np.testing.assert_allclose(
        transform_points(transformation, case["points"], case["dims"]), case["expected"], atol=case["tolerance"]
    )

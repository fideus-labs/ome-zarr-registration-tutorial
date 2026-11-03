"""Step 4. Apply the transformation from the scene alone, lazily, without writing a resampled copy of the images.

    python steps/apply.py SCENE.ozx [FIXED_LABELS MOVING_LABELS] [--show]

The labels are optional: two OME-Zarr label images on the two sides, carried through the same transformation.
--show opens the scene in napari at the end, which places the moving image through the affine itself.
"""

import sys
from pathlib import Path

import ngff_zarr as nz
import numpy as np
from common import dice, ncc, overlay, scene_fields
from ngff_zarr.v06.zarr_metadata import Identity

SHOW = "--show" in sys.argv
arguments = [argument for argument in sys.argv[1:] if argument != "--show"]
SCENE = arguments[0] if arguments else "output/pair.ozx"
LABELS = arguments[1:3]
if not Path(SCENE).exists():
    sys.exit(f"{SCENE}: no such scene")

scene = nz.NgffScene.from_ome_zarr(SCENE)
transformation = scene.coordinateTransformations[0]
if transformation.type not in ("affine", "displacements"):
    sys.exit(f"{SCENE}: holds a '{transformation.type}'; this step applies an affine or a displacements field")
fixed = scene.images[transformation.input.path].images[0]
moving = scene.images[transformation.output.path].images[0]
fields = scene_fields(SCENE, transformation)
print(
    f"The scene holds an RFC-5 '{transformation.type}' from {transformation.input.path} to {transformation.output.path}"
)

# Lazy: this describes the result, block by block. Nothing is read or computed yet.
moved = nz.resample(transformation, fixed, moving, fields=fields)
# "Before" is the moving image on the fixed grid as the two sit in space: the identity, through the same call.
unmoved = nz.resample(Identity(input=transformation.input, output=transformation.output), fixed, moving)

# One plane is computed (a 2-D image is one plane), reading only the part of the moving image it needs.
plane = (fixed.data.shape[0] // 2,) if fixed.data.ndim == 3 else ()
fixed_plane, moved_plane = np.asarray(fixed.data[plane]), np.asarray(moved.data[plane])
after = Path(SCENE).parent / "after.png"
overlay(fixed_plane, moved_plane, after)
before = ncc(fixed_plane, np.asarray(unmoved.data[plane]))
print(f"Correlation with the fixed image, on one plane: {before:.2f} -> {ncc(fixed_plane, moved_plane):.2f}")
print(f"After registration: {after}")

# The same transformation carries everything else on the moving side, labels included, with their values kept.
if LABELS:
    labels_fixed, labels_moving = (nz.from_ngff_zarr(path).images[0] for path in LABELS)
    carried = nz.resample(transformation, fixed, labels_moving, interpolator="label_image", fields=fields)
    print(
        f"Binary mask Dice of the labels: {dice(labels_fixed.data, labels_moving.data):.2f} -> {dice(labels_fixed.data, carried.data):.2f}"
    )

# A viewer that reads RFC-5: napari-ome-zarr opens the scene folder and applies the affine itself (not a field yet).
if SHOW:
    import napari

    viewer = napari.Viewer()
    viewer.open(SCENE.removesuffix(".ozx") + ".ome.zarr", plugin="napari-ome-zarr")
    napari.run()

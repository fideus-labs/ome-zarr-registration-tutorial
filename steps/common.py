"""What the steps share: where the data is, a picture of two planes, two measures, and the two moves of a
transformation into and out of a scene."""

import json
import os
import shutil
from pathlib import Path

import ngff_zarr as nz
import numpy as np
from ngff_zarr.v06.zarr_metadata import Displacements
from PIL import Image

#: The organoid, two rounds and their nuclei, as get_data.py writes them. The same stores on a server read the same way:
#: ORGANOID_DATA=https://a.server/organoid points the steps there.
DATA = os.environ.get("ORGANOID_DATA", str(Path(__file__).resolve().parent.parent / "output" / "data"))

#: Where a displacements field lives inside a scene: an image of the scene, named by its path.
FIELD = "coordinateTransformations/registration"


def scene_transformation(transform, store):
    """The RFC-5 transformation step 2 wrote at ``transform``, ready for a fresh scene at ``store``.

    An affine is metadata alone: it is read as it is. A displacements field is an image of vectors: it is copied
    below the scene first, and the scene points at it by its path (ngff-zarr writes a scene in that order).
    """
    shutil.rmtree(store, ignore_errors=True)
    with open(f"{transform}/zarr.json", encoding="utf-8") as file:
        ome = json.load(file)["attributes"]["ome"]
    if "multiscales" not in ome:
        return nz.from_ome_zarr(transform, kind="transformation")
    nz.to_ome_zarr(f"{store}/{FIELD}", nz.from_ome_zarr(transform), version="0.6")
    return Displacements(path=FIELD, interpolation="linear")


def scene_fields(scene, transformation):
    """What ``nz.resample`` needs beside the transformation: a displacements field, read from the scene by its path.

    An affine needs nothing: ngff-zarr reads its matrix with the scene, inline or from the array its own path names.
    """
    path = transformation.path if transformation.type == "displacements" else None
    return {path: nz.from_ome_zarr(f"{scene}/{path}")} if path else None


def view(fixed, moved):
    """The fixed image in green and the moved one in magenta, in napari. ``moved`` can stay lazy: napari computes only
    the plane on screen, so this works for an affine and for a displacements field."""
    import napari

    viewer = napari.Viewer()
    middle = (fixed.data.shape[0] // 2,) if fixed.data.ndim == 3 else ()
    for image, colormap in ((fixed, "green"), (moved, "magenta")):
        limits = np.percentile(np.asarray(image.data[middle]), (1, 99.8))
        viewer.add_image(
            image.data, scale=list(image.scale.values()), colormap=colormap, blending="additive", contrast_limits=limits
        )
    return viewer


def _scaled(plane):
    plane = np.asarray(plane, float)
    low, high = np.percentile(plane, (1, 99.8))
    return np.clip((plane - low) / max(high - low, 1e-6), 0, 1)


def show(fixed, moving, path=None):
    """The two planes in one picture, fixed in green, moving in magenta: where they agree, it turns white.

    Returns the picture, which a notebook displays as the cell's last line; ``path`` also saves it.
    """
    green, magenta = _scaled(fixed), _scaled(moving)
    picture = Image.fromarray((np.stack([magenta, green, magenta], axis=-1) * 255).astype(np.uint8))
    if path:
        picture.save(path)
    return picture


def ncc(fixed, moving):
    """Normalized cross-correlation over the tissue: 1 is a perfect match."""
    fixed, moving = np.asarray(fixed, float), np.asarray(moving, float)
    tissue = fixed > np.percentile(fixed, 60)
    a, b = fixed[tissue] - fixed[tissue].mean(), moving[tissue] - moving[tissue].mean()
    return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))


def dice(a, b):
    """Dice of the two binary masks (any label against none): 1 is a perfect overlap of the masks, not of each label."""
    a, b = np.asarray(a) > 0, np.asarray(b) > 0
    return float(2 * (a & b).sum() / (a.sum() + b.sum()))

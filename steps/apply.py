"""Step 4. Apply the transformation, from the scene alone, without ever writing a resampled copy of the images."""

import sys
from pathlib import Path

import ngff_zarr as nz
import numpy as np
from common import dice, ncc, overlay

SCENE = sys.argv[1] if len(sys.argv) > 1 else "output/pair.ozx"

scene = nz.NgffScene.from_ome_zarr(SCENE)
transformation = scene.coordinateTransformations[0]
fixed = scene.images["fixed"].images[0]
moving = scene.images["moving"].images[0]
fields = {transformation.path: nz.from_ome_zarr(f"{SCENE}/{transformation.path}")}
print(f"The scene holds an RFC-5 '{transformation.type}' from {transformation.input.path} to {transformation.output.path}")

# Lazy: this describes the result, block by block. Nothing is read or computed yet.
moved = nz.resample(transformation, fixed, moving, fields=fields)

# One plane is computed (a 2-D image is one), reading only the part of the moving image it needs.
plane = (fixed.data.shape[0] // 2,) if fixed.data.ndim == 3 else ()
fixed_plane, moved_plane = np.asarray(fixed.data[plane]), np.asarray(moved.data[plane])
overlay(fixed_plane, moved_plane, "output/after.png")
print(f"Correlation with the fixed image, on one plane: {ncc(fixed_plane, np.asarray(moving.data[plane])):.2f} -> {ncc(fixed_plane, moved_plane):.2f}")
print("After registration: output/after.png")

# The same transformation carries everything else on the moving side: the nuclei of step 1, on a scene of that pair.
stores = {name: Path(f"output/{name}_nuclei.ome.zarr") for name in ("R0", "R1")}
nuclei = {name: nz.from_ngff_zarr(str(store)).images[0] for name, store in stores.items() if store.exists()}
if len(nuclei) == 2 and np.squeeze(nuclei["R0"].data).shape == fixed.data.shape:
    carried = nz.resample(transformation, fixed, nuclei["R1"], interpolator="label_image", fields=fields)
    before = dice(np.squeeze(nuclei["R0"].data), np.squeeze(nuclei["R1"].data))
    after = dice(np.squeeze(nuclei["R0"].data), np.squeeze(carried.data))
    print(f"Overlap of the nuclei (Dice): {before:.2f} -> {after:.2f}")

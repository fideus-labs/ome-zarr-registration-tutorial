"""Step 3. Read the scene back: what any OME-Zarr 0.6 reader finds in the file."""

import sys

import ngff_zarr as nz
import numpy as np

scene = nz.NgffScene.from_ome_zarr(sys.argv[1] if len(sys.argv) > 1 else "output/pair.ozx")

for name, multiscales in scene.images.items():
    size = " x ".join(str(extent) for extent in multiscales.images[0].data.shape)
    print(f"{name}: {size} voxels, {len(multiscales.images)} levels")

transformation = scene.coordinateTransformations[0]
print(f"transformation: {transformation.type}, from {transformation.input.path} to {transformation.output.path}")
if transformation.type == "affine":
    with np.printoptions(precision=2, suppress=True):
        print(np.asarray(transformation.affine))
else:
    print(f"its field is stored in {transformation.path}")

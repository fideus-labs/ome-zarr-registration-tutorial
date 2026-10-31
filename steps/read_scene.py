"""Step 3. Read the scene back: what any OME-Zarr 0.6 reader finds in the file."""

import sys

import ngff_zarr as nz
import numpy as np

SCENE = sys.argv[1] if len(sys.argv) > 1 else "output/pair.ozx"

scene = nz.NgffScene.from_ome_zarr(SCENE)

for name, multiscales in scene.images.items():
    size = " x ".join(str(extent) for extent in multiscales.images[0].data.shape)
    print(f"{name}: {size} voxels, {len(multiscales.images)} levels")

transformation = scene.coordinateTransformations[0]
print(f"transformation: {transformation.type}, from {transformation.input.path} to {transformation.output.path}")

field = nz.from_ome_zarr(f"{SCENE}/{transformation.path}").images[0]
print(f"its field: {transformation.path}, {' x '.join(str(extent) for extent in field.data.shape)}")
centre = tuple(extent // 2 for extent in field.data.shape[1:])
dz, dy, dx = np.asarray(field.data[(slice(None), *centre)])
print(f"at the centre of the image: dz {dz:.1f}, dy {dy:.1f}, dx {dx:.1f} {field.axes_units['x']}s")

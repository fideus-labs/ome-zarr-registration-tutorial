"""Step 3. Write the registration as one OME-Zarr 0.6 scene, with ngff-zarr alone.

    python steps/write.py FIXED MOVING TRANSFORM SCENE.ozx [--overwrite]

The transformation is the one step 2 wrote: an RFC-5 ``affine`` or a ``displacements`` field, in OME-Zarr.
"""

import sys
from pathlib import Path

import ngff_zarr as nz
from common import scene_transformation
from ngff_zarr import CoordinateSystemIdentifier, NgffScene

OVERWRITE = "--overwrite" in sys.argv
FIXED, MOVING, TRANSFORM, SCENE = [argument for argument in sys.argv[1:] if argument != "--overwrite"] or (
    "output/data/fixed.ome.zarr",
    "output/data/moving.ome.zarr",
    "output/registration/P000/Transform.ome.zarr",
    "output/pair.ozx",
)
STORE = SCENE.removesuffix(".ozx") + ".ome.zarr"

for path in (FIXED, MOVING, TRANSFORM):
    if not Path(path, "zarr.json").is_file():
        sys.exit(f"{path}: not an OME-Zarr store (no zarr.json in it)")
if Path(STORE).exists() and not OVERWRITE:
    sys.exit(f"{STORE} exists: pass --overwrite to replace it")

# An affine goes into the scene's metadata; a displacements field is copied below the scene, and pointed at.
registration = scene_transformation(TRANSFORM, STORE)

# The scene names what it connects: from the coordinates of the fixed image to those of the moving one.
registration.input = CoordinateSystemIdentifier(path="fixed", name="intrinsic")
registration.output = CoordinateSystemIdentifier(path="moving", name="intrinsic")
images = {"fixed": nz.from_ome_zarr(FIXED), "moving": nz.from_ome_zarr(MOVING)}
NgffScene(images=images, coordinateTransformations=[registration]).to_ome_zarr(STORE, overwrite=False)

# One file: the same store, zipped (RFC-9).
nz.write_store_to_zip(STORE, SCENE, version="0.6")
print(f"Scene: {SCENE}, holding an RFC-5 '{registration.type}' from fixed to moving")

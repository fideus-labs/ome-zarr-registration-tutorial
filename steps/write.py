"""Step 3. Write the registration as one OME-Zarr 0.6 scene, with ngff-zarr alone."""

import sys

import ngff_zarr as nz
from ngff_zarr import CoordinateSystemIdentifier, NgffScene
from ngff_zarr.v06.zarr_metadata import Displacements

FIXED, MOVING, TRANSFORM, SCENE = sys.argv[1:] or (
    "output/R0.ome.zarr",
    "output/R1.ome.zarr",
    "output/registration/P000/Transform.ome.zarr",
    "output/pair.ozx",
)
STORE = SCENE.removesuffix(".ozx") + ".ome.zarr"
FIELD = "coordinateTransformations/registration"

# The transformation is an OME-Zarr image already: it goes below the scene, first.
nz.to_ome_zarr(f"{STORE}/{FIELD}", nz.from_ome_zarr(TRANSFORM), version="0.6")

# The scene names what it connects: from the coordinates of the fixed image to those of the moving one.
registration = Displacements(
    path=FIELD,
    interpolation="linear",
    input=CoordinateSystemIdentifier(path="fixed", name="intrinsic"),
    output=CoordinateSystemIdentifier(path="moving", name="intrinsic"),
)
images = {"fixed": nz.from_ome_zarr(FIXED), "moving": nz.from_ome_zarr(MOVING)}
NgffScene(images=images, coordinateTransformations=[registration]).to_ome_zarr(STORE, overwrite=False)

# One file: the same store, zipped (RFC-9).
nz.write_store_to_zip(STORE, SCENE, version="0.6")
print(f"Scene: {SCENE}")

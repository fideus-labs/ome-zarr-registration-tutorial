"""Make tests/fixture: a small OME-Zarr 0.6 scene holding the tutorial's actual affine, and the points it maps.

    python tests/make_fixture.py [TRANSFORM.ome.zarr]

The two images are 4 x 4 x 4 voxels at the organoid's spacing: the scene is a few kilobytes, and the transformation
is the twelve numbers step 2 found. Another reader opens `organoid_affine.ozx`, takes its affine, maps `points.json`'s
points (micrometers, in the order z, y, x) and compares with `expected`, within `tolerance`.
"""

import json
import shutil
import sys
from pathlib import Path

import ngff_zarr as nz
import numpy as np
from ngff_zarr import CoordinateSystemIdentifier, NgffScene
from ngff_zarr.transform_points import transform_points

HERE = Path(__file__).parent
TRANSFORM = sys.argv[1] if len(sys.argv) > 1 else "output/registration/P000/Transform.ome.zarr"
POINTS = [[15.0, 73.0, 58.0], [0.0, 0.0, 0.0], [29.4, 147.3, 115.9]]

registration = nz.from_ome_zarr(TRANSFORM, kind="transformation")
registration.input = CoordinateSystemIdentifier(path="fixed", name="intrinsic")
registration.output = CoordinateSystemIdentifier(path="moving", name="intrinsic")


def tiny(seed):
    image = nz.NgffImage(
        data=np.random.default_rng(seed).integers(0, 1000, (4, 4, 4)).astype(np.uint16),
        dims=["z", "y", "x"],
        scale={"z": 0.6, "y": 0.2166666666666666, "x": 0.2166666666666666},
        translation={"z": 0.0, "y": 0.0, "x": 0.0},
        axes_units={"z": "micrometer", "y": "micrometer", "x": "micrometer"},
    )
    return nz.to_multiscales(image, scale_factors=[])


store = HERE / "fixture" / "organoid_affine.ome.zarr"
shutil.rmtree(store, ignore_errors=True)
NgffScene(images={"fixed": tiny(0), "moving": tiny(1)}, coordinateTransformations=[registration]).to_ome_zarr(
    store, overwrite=False
)
nz.write_store_to_zip(store, store.with_suffix("").with_suffix(".ozx"), version="0.6")
shutil.rmtree(store)

case = {
    "scene": "organoid_affine.ozx",
    "transformation": 0,
    "dims": ["z", "y", "x"],
    "unit": "micrometer",
    "points": POINTS,
    "expected": transform_points(registration, POINTS, ["z", "y", "x"]).tolist(),
    "tolerance": 1e-4,
}
(HERE / "fixture" / "points.json").write_text(json.dumps(case, indent=2) + "\n", encoding="utf-8")
print(json.dumps(case["expected"]))

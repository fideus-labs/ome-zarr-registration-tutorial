"""The SmartSPIM template moved onto the CCF at 10 um: the registration's transformation applied to the finest level of the
two stores on S3, reoriented the same way, materialized on the CCF's 10 um grid for a viewer. python use-cases/mouse-brain/moved_10um.py"""

import sys
import time
from pathlib import Path

import dask.array as da
import ngff_zarr as nz

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "steps"))  # the tutorial's common.py
from common import scene_fields  # noqa: E402
from read_templates import ANON, TEMPLATES, reoriented  # noqa: E402  (importing runs nothing: guarded below)

OUTPUT = Path(__file__).resolve().parent / "output"
t = time.time()
ccf = nz.from_ngff_zarr(TEMPLATES["ccf"][0], storage_options=ANON).images[0]
smartspim = nz.from_ngff_zarr(TEMPLATES["smartspim"][0], storage_options=ANON).images[0]
moving, _, _ = reoriented(smartspim, ccf)
fixed = nz.NgffImage(
    data=ccf.data,
    dims=list(ccf.dims),
    scale=dict(ccf.scale),
    translation={d: 0.0 for d in ccf.dims},
    axes_units=dict(ccf.axes_units),
    axes_orientations=ccf.axes_orientations,
)
moving = nz.NgffImage(
    data=moving.data,
    dims=list(moving.dims),
    scale=dict(moving.scale),
    translation={d: 0.0 for d in moving.dims},
    axes_units=dict(moving.axes_units),
    axes_orientations=moving.axes_orientations,
)
scene = nz.NgffScene.from_ome_zarr(str(OUTPUT / "fireants.ozx"))
transformation = scene.coordinateTransformations[0]
moved = nz.resample(transformation, fixed, moving, fields=scene_fields(str(OUTPUT / "fireants.ozx"), transformation))
print(f"described in {time.time() - t:.0f} s: {moved.data.shape} at {fixed.scale}", flush=True)
image = nz.NgffImage(
    data=da.asarray(moved.data).rechunk((64, 128, 128)),
    dims=list(fixed.dims),
    scale=dict(fixed.scale),
    translation=dict(fixed.translation),
    axes_units=dict(fixed.axes_units),
    axes_orientations=fixed.axes_orientations,
)
nz.to_ngff_zarr(
    OUTPUT / "smartspim_on_ccf_10um.ome.zarr", nz.to_multiscales(image, scale_factors=[2, 4]), version="0.5"
)
print(f"written in {time.time() - t:.0f} s", flush=True)

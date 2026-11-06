"""Resample a moving image onto a fixed image's grid through a sequence of ITK transforms, and write OME-Zarr.

    python steps/resample.py FIXED MOVING TRANSFORM [TRANSFORM ...] -o OUT.ome.zarr [--spacing MM]
                             [--storage-options JSON]

FIXED, MOVING: OME-Zarr images, local or remote (s3://, https://). Only FIXED's grid is used, never its pixels.
TRANSFORM: ITK transform files (.h5, .tfm: an affine, a B-spline, a composite), applied in the order given, from the
fixed image's points to the moving image's.
--spacing: fill FIXED's extent on a finer (or coarser) grid, in mm.

Both images are taken in millimeters and (z, y, x) order, as ITK transforms are, whatever their stores declare. The
moving level read is the coarsest one as fine as the output grid. Lazy: the output is written block by block, and
each block reads only the moving chunks it lands on.
"""

import argparse
import json
import time

import dask.array as da
import itk
import ngff_zarr as nz
import numpy as np

MM = {"millimeter": 1.0, "micrometer": 1e-3, "nanometer": 1e-6, "meter": 1e3, None: 1.0}


def in_mm(image):
    """``image`` in (z, y, x) order and mm, other axes at their first index: a lazy view."""
    spatial = [d for d in image.dims if d in "zyx"]
    unit = {d: MM[(image.axes_units or {}).get(d)] for d in spatial}
    return nz.NgffImage(
        data=image.data[tuple(slice(None) if d in "zyx" else 0 for d in image.dims)].transpose(
            [spatial.index(d) for d in "zyx"]
        ),
        dims=["z", "y", "x"],
        scale={d: image.scale[d] * unit[d] for d in "zyx"},
        translation={d: image.translation[d] * unit[d] for d in "zyx"},
        name=image.name,
    )


parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
parser.add_argument("fixed")
parser.add_argument("moving")
parser.add_argument("transforms", nargs="+", help="ITK transform files, applied in this order")
parser.add_argument("-o", "--output", required=True)
parser.add_argument("--spacing", type=float, help="output spacing in mm (default: the fixed image's)")
parser.add_argument("--storage-options", type=json.loads, help="e.g. '{\"skip_signature\": true}'")
args = parser.parse_args()

fixed = in_mm(nz.from_ngff_zarr(args.fixed, storage_options=args.storage_options).images[0])
if args.spacing:
    origin = np.array([fixed.translation[d] for d in "zyx"])
    extent = np.array([fixed.scale[d] * n for d, n in zip("zyx", fixed.data.shape, strict=True)])
    shape = tuple(np.maximum(1, np.round(extent / args.spacing)).astype(int))
    start = origin - np.array([fixed.scale[d] for d in "zyx"]) / 2 + args.spacing / 2  # the same extent
    fixed = nz.NgffImage(
        data=da.zeros(shape, dtype=np.uint8, chunks=128),
        dims=["z", "y", "x"],
        scale=dict.fromkeys("zyx", args.spacing),
        translation=dict(zip("zyx", start.tolist())),
    )

transform = itk.CompositeTransform[itk.D, 3].New()
for path in reversed(args.transforms):  # a composite applies the transform added last first
    transform.AddTransform(itk.transformread(path)[0])

pyramid = nz.from_ngff_zarr(args.moving, storage_options=args.storage_options).images
spacing = min(fixed.scale.values())
level = max([0] + [i for i, image in enumerate(pyramid) if max(in_mm(image).scale.values()) <= spacing * 1.01])
moving = in_mm(pyramid[level])
print(
    f"{fixed.data.shape} voxels at {spacing * 1000:.2f} um, read from moving level {level} "
    f"({min(moving.scale.values()) * 1000:.2f} um), through {len(args.transforms)} transform(s)"
)

moved = nz.resample(transform, fixed, moving)
moved.axes_units = dict.fromkeys("zyx", "millimeter")
start_time = time.time()
nz.to_ngff_zarr(args.output, nz.to_multiscales(moved, scale_factors=[]))
print(f"{args.output}, written in {time.time() - start_time:.0f} s")

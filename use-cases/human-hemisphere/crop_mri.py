"""A small fixed image: a cube of the MRI, read from S3 and written locally.

python crop_mri.py Z Y X SIZE_MM OUT.ome.zarr     # the cube's centre, in the MRI's physical frame (mm)
"""

import sys

import ngff_zarr as nz
import numpy as np
from hemisphere import mri

centre, size, out = np.array([float(v) for v in sys.argv[1:4]]), float(sys.argv[4]), sys.argv[5]
image = mri(0)
scale = np.array([image.scale[d] for d in "zyx"])
origin = np.array([image.translation[d] for d in "zyx"])
lo = np.floor((centre - size / 2 - origin) / scale).astype(int)
hi = np.ceil((centre + size / 2 - origin) / scale).astype(int)
cube = nz.NgffImage(
    data=np.asarray(image.data[lo[0] : hi[0], lo[1] : hi[1], lo[2] : hi[2]]),
    dims=["z", "y", "x"],
    scale={d: image.scale[d] for d in "zyx"},
    translation={d: float(origin[i] + lo[i] * scale[i]) for i, d in enumerate("zyx")},
    axes_units=dict.fromkeys("zyx", "millimeter"),
    name="mri",
)
nz.to_ngff_zarr(out, nz.to_multiscales(cube, scale_factors=[]))
print(f"{out}: {cube.data.shape} voxels of {scale[0]:.3f} mm")

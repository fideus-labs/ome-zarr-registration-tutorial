"""One time point and channel of idr0044, read over HTTP, into a local OME-Zarr store with its true geometry.

python demo/read_idr0044.py TIME LEVEL OUTPUT.ome.zarr
"""

import sys

import ngff_zarr as nz

URL = "https://livingobjects.ebi.ac.uk/idr/zarr/v0.4/idr0044A/4007801.zarr"
# The store declares a scale of 1.0: the voxel size comes from the paper (McDole et al. 2018, experiment A).
Z_UM, XY_UM = 2.031, 0.325

time, level, output = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
xy = XY_UM * 2**level  # the store's levels halve x and y only
image = nz.NgffImage(
    data=nz.from_ngff_zarr(URL).images[level].data[time, 0].rechunk((64, 256, 256)),
    dims=["z", "y", "x"],
    scale={"z": Z_UM, "y": xy, "x": xy},
    translation=dict.fromkeys("zyx", 0.0),
    axes_units=dict.fromkeys("zyx", "micrometer"),
)
nz.to_ngff_zarr(output, nz.to_multiscales(image), version="0.5")
print(f"t{time}, level {level}: {image.data.shape} -> {output}")

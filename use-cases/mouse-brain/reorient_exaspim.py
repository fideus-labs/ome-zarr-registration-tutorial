"""Put the ExaSPIM template on the CCF's anatomical axes: python use-cases/mouse-brain/reorient_exaspim.py

The store declares no orientation. Its middle planes show the head in profile on a y plane (nose along +x, dorsal
along -z) and a coronal section on an x plane, so: x runs posterior to anterior, z dorsal to ventral, y across the
head. The CCF's axes are z anterior to posterior, y dorsal to ventral, x left to right. Hence new z = old x reversed,
new y = old z, new x = old y. The left-right handedness of y is not known from the pictures: a mirrored brain is
symmetric enough to register either way, and the labels say so.
"""

from pathlib import Path

import dask.array as da
import ngff_zarr as nz

OUTPUT = Path(__file__).resolve().parent / "output"
source = nz.from_ngff_zarr(OUTPUT / "exaspim.ome.zarr").images[0]
ccf = nz.from_ngff_zarr(OUTPUT / "ccf.ome.zarr").images[0]

data = source.data.transpose(2, 0, 1)[::-1]  # (x, z, y) of the old store, the new z reversed
scale = {"z": source.scale["x"], "y": source.scale["z"], "x": source.scale["y"]}
image = nz.NgffImage(
    data=da.asarray(data).rechunk((64, 128, 128)),
    dims=["z", "y", "x"],
    scale=scale,
    translation={d: 0.0 for d in "zyx"},
    axes_units=dict(source.axes_units),
    axes_orientations=ccf.axes_orientations,  # x's handedness assumed; see the docstring
)
nz.to_ngff_zarr(OUTPUT / "exaspim_on_ccf_axes.ome.zarr", nz.to_multiscales(image, scale_factors=[2, 4]), version="0.5")
print(
    f"exaspim_on_ccf_axes.ome.zarr: {image.data.shape} voxels of {scale['z']:.4g} x {scale['y']:.4g} x {scale['x']:.4g} {source.axes_units['x']}"
)

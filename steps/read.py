"""Step 1. Open two rounds of an organoid straight from Zenodo, without downloading the archive."""

from pathlib import Path

import fsspec
import ngff_zarr as nz
import numpy as np
from common import overlay

ARCHIVE = "https://zenodo.org/records/13982701/files/220605_151046.zarr.zip"
WELL = "220605_151046.zarr/C/02"

archive = fsspec.filesystem("zip", fo=fsspec.open(ARCHIVE).open())
rounds = {name: nz.from_ngff_zarr(archive.get_mapper(f"{WELL}/{i}")) for name, i in (("R0", 0), ("R1", 1))}

for name, multiscales in rounds.items():
    image = multiscales.images[0]
    size = " x ".join(str(image.data.shape[image.dims.index(axis)]) for axis in "zyx")
    voxel = " x ".join(f"{image.scale[axis]:.3g}" for axis in "zyx")
    print(f"{name}: {size} voxels of {voxel} {image.axes_units['x']}s, {len(multiscales.images)} levels")

# Nothing is in memory yet. This reads one plane, of one level (dims c, z, y, x), of each round.
Path("output").mkdir(exist_ok=True)
fixed_plane, moving_plane = (np.asarray(rounds[name].images[2].data[0, 25]) for name in rounds)
overlay(fixed_plane, moving_plane, "output/before.png")
print("Before registration: output/before.png")

# The registration reads local stores: a copy of the images, and of their nuclei for step 4.
for name, i in (("R0", 0), ("R1", 1)):
    nz.to_ngff_zarr(f"output/{name}.ome.zarr", rounds[name], version="0.5")
    nuclei = nz.from_ngff_zarr(archive.get_mapper(f"{WELL}/{i}/labels/nuc"))
    nz.to_ngff_zarr(f"output/{name}_nuclei.ome.zarr", nuclei, version="0.5")
print("Local stores: output/R0.ome.zarr, output/R1.ome.zarr")

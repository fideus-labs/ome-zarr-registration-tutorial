"""Get the data, once: the two rounds of the organoid and their nuclei, out of the Zenodo plate, into output/data/.

    python steps/get_data.py

The plate (38 MB, a Fractal HCS plate in one zip) is downloaded once and kept beside the data. Each round comes out as
one store of its DAPI channel, with its geometry and its pyramid, and its nuclei labels as another: four OME-Zarr 0.5
stores, 46 MB, that the steps read like any other, from this folder or from a server.
"""

import sys
import urllib.request
from pathlib import Path

import fsspec
import ngff_zarr as nz

ARCHIVE = "https://zenodo.org/records/13982701/files/220605_151046.zarr.zip"
WELL = "220605_151046.zarr/C/02"
ROUNDS = {"fixed": 0, "moving": 1}  # round 0 is the reference, round 1 is brought onto it
DATA = Path(__file__).resolve().parent.parent / "output" / "data"

stores = [DATA / f"{name}{suffix}.ome.zarr" for name in ROUNDS for suffix in ("", "_nuclei")]
if all((store / "zarr.json").is_file() for store in stores):
    sys.exit(f"The data is there already: {DATA}")
DATA.mkdir(parents=True, exist_ok=True)

plate = DATA.parent / ARCHIVE.rsplit("/", 1)[1]
if not plate.exists():
    print(f"Downloading the plate, 38 MB: {ARCHIVE}", flush=True)
    urllib.request.urlretrieve(ARCHIVE, plate)

archive = fsspec.filesystem("zip", fo=str(plate))
for name, index in ROUNDS.items():
    image = nz.from_ngff_zarr(archive.get_mapper(f"{WELL}/{index}")).images[0]  # dims c, z, y, x
    dapi = nz.NgffImage(
        data=image.data[0],
        dims=["z", "y", "x"],
        scale={axis: image.scale[axis] for axis in "zyx"},
        translation={axis: image.translation[axis] for axis in "zyx"},
        axes_units={axis: image.axes_units[axis] for axis in "zyx"},
    )
    nz.to_ngff_zarr(DATA / f"{name}.ome.zarr", nz.to_multiscales(dapi), version="0.5")
    nz.to_ngff_zarr(
        DATA / f"{name}_nuclei.ome.zarr",
        nz.from_ngff_zarr(archive.get_mapper(f"{WELL}/{index}/labels/nuc")),
        version="0.5",
    )
    print(
        f"{name}: round {index}, {' x '.join(str(extent) for extent in dapi.data.shape)} voxels, and its nuclei",
        flush=True,
    )
print(f"Done: {DATA}")

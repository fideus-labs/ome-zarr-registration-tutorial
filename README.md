# Registration with OME-Zarr

**Register two images and keep everything in OME-Zarr: both images and the transformation, never a resampled copy.**

| The tutorial: two rounds of an organoid | At scale: two time points of a mouse embryo |
|---|---|
| <img src="media/organoid.gif" width="340" alt="An organoid before and after registration"> | <img src="media/embryo.gif" width="340" alt="A mouse embryo before and after registration"> |

An organoid was imaged in two rounds of staining and moved in between. A registration usually leaves you with a
resampled copy of the data and a transform only one tool can read. Here you end with one OME-Zarr file that holds the
two images and the transformation between them (RFC-5), and you apply it only when you need it.

[Overview video](media/videos/0-overview.mp4) (1 min).

## The four steps

About 30 minutes, 3 of them computing. Each notebook is saved with its outputs, so you can read it before running it.

| Step | What you do | With | Video |
|---|---|---|---|
| [1. Read](steps/1-read.ipynb) | Open both images and read one resolution or one box, from disk or from a server | ngff-zarr | [1 min](media/videos/1-read.mp4) |
| [2. Register](steps/2-register.ipynb) | Align the moving image to the fixed one with one command, and get an RFC-5 `affine` | IMPACT-Reg | [1 min](media/videos/2-register.mp4) |
| [3. Write](steps/3-write.ipynb) | Put both images and the transformation in one file, `pair.ozx`, and read it back | ngff-zarr | [1 min](media/videos/3-write.mp4) |
| [4. Apply](steps/4-apply.ipynb) | Apply it lazily to the image, the nuclei and a point, and view the result in napari | ngff-zarr, napari | [1 min](media/videos/4-apply.mp4) |

Only step 2 uses KonfAI. Steps 3 and 4 take any RFC-5 transformation, an `affine` or a `displacements` field, so they
run unchanged with a deformable preset or with a registration tool of your own.

## Install

Python 3.12 or newer, no GPU needed. Install before the session: torch and the registration engines are large
downloads.

```bash
git clone https://github.com/fideus-labs/ome-zarr-registration-tutorial
cd ome-zarr-registration-tutorial
uv venv --python 3.12
uv pip install -r requirements.txt
uv run python steps/get_data.py        # the data, 38 MB, once
uv run jupyter lab steps/1-read.ipynb
```

Without [uv](https://docs.astral.sh/uv/): `python -m venv .venv`, activate it, then `pip install -r requirements.txt`
and the same two commands without `uv run`.

It runs on Linux, Windows and Apple-silicon macOS. `ConvexAdam_Composite` has no macOS package, and the FireANTs presets
need a GPU. napari needs a desktop: on a headless machine, skip the last cell of step 4.

## The data

[Zenodo 13982701](https://zenodo.org/records/13982701): one organoid in two rounds, DAPI, 50 × 680 × 535 voxels of
0.6 × 0.217 × 0.217 µm, with its nuclei labels. 38 MB, by Nicole Repina (FMI), CC-BY 4.0. `get_data.py` takes the two
rounds of well C/02 and their nuclei out of the plate, into `output/data/`. To read them from a server instead, set
`ORGANOID_DATA=https://a.server/organoid`.

## Scripts

The steps as commands, for your own images:

```bash
python steps/write.py FIXED MOVING Transform.ome.zarr pair.ozx        # step 3
python steps/apply.py pair.ozx [FIXED_LABELS MOVING_LABELS]           # step 4
python steps/resample.py FIXED MOVING a.h5 b.h5 -o moved.ome.zarr     # resample through ITK transforms
```

`resample.py` applies ITK transforms (an affine, a B-spline, several in a row) and reads only the part of the moving
image the fixed grid needs.

## In 3D Slicer

Install the [SlicerOMEZarr](https://github.com/fideus-labs/SlicerOMEZarr) extension and drag `output/pair.ome.zarr`
onto Slicer: you get both images, and the transformation as a transform node. Slicer needs ngff-zarr 0.52 or newer:
run `slicer.util.pip_install("ngff-zarr[remote]>=0.52")` in its Python console if it has an older one.

## Going further

- **[Going further](going-further.md):** your own images, 2-D images, which way the transformation goes, what is lazy.
- **[Use cases](use-cases/README.md)** ([video](media/videos/5-at-scale.mp4)): the same steps on real data.
  - [A mouse embryo](use-cases/mouse-embryo/README.md): two time points of a 9.3 TB light-sheet series.
  - [Mouse brains](use-cases/mouse-brain/README.md): two Allen templates from S3, rigid and deformable.
    [Video](media/videos/two-mouse-brains.mp4): up to 1.2 billion voxels on a laptop GPU.
  - [A human hemisphere](use-cases/human-hemisphere/README.md): an 8 mm cube filled from a 976 GB synchrotron scan,
    reading 0.24 GB of it.
- **[Tests](tests/test_rfc5.py):** RFC-5 round trips with ngff-zarr alone, run in CI. [`tests/fixture/`](tests/fixture/)
  is a small scene with the tutorial's affine, to check another reader against.

## OME-Zarr Hackathon 2026

Part of the *Image Registration Workflows with OME-Zarr* topic, Zürich, 2 to 6 November 2026, led by Valentin Boussot
(KonfAI, IMPACT-Reg) and Matt McCormick (Fideus Labs, ngff-zarr). Done during the week:

- **IMPACT-Reg 1.8.8** ([KonfAI v1.8.8](https://github.com/fideus-labs/KonfAI/releases/tag/v1.8.8)): a linear preset
  writes an RFC-5 `affine`, a few kB instead of a field ([#304](https://github.com/fideus-labs/KonfAI/pull/304));
  OME-Zarr in and out, 2-D images, presets in voxels.
- **ngff-zarr 0.52**: a lazy `resample` that reads only what each block needs, for affine, B-spline and field
  ([#771](https://github.com/fideus-labs/ngff-zarr/pull/771)); a remote `.ozx` read in place
  ([#826](https://github.com/fideus-labs/ngff-zarr/pull/826)); an affine's matrix stored as an array
  ([#828](https://github.com/fideus-labs/ngff-zarr/pull/828)).
- **3D Slicer** opens OME-Zarr 0.6 scenes ([SlicerOMEZarr #15](https://github.com/fideus-labs/SlicerOMEZarr/pull/15)).
- **Still open**: napari-ome-zarr 0.11 reads neither a `displacements` field nor an affine stored as an array, so the
  tutorial shows the result in napari through ngff-zarr's lazy resample.

## License

Code and text: [MIT](LICENSE). Data: CC-BY 4.0, as stated on its Zenodo record.

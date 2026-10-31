# Going further

## Your own pair

Any two images that should line up: two time points, two rounds, two samples, two modalities.

```bash
impact-reg-konfai register Generic_Rigid -f fixed.ome.zarr -m moving.ome.zarr -o output/mine --cpu 4 \
    --set Predictor.outputs_dataset.DisplacementField.OutputDataset.dataset_filename=Transform:omezarr
python steps/write.py fixed.ome.zarr moving.ome.zarr output/mine/P000/Transform.ome.zarr output/mine.ozx
python steps/apply.py output/mine.ozx
```

What to check first:

| Your data | What to do |
|---|---|
| Several channels or time points | Register one image: write the channel or the time point to a store of its own, as [`read.py`](steps/read.py) does |
| On a server or in a zip | Copy or unzip it first: `register` reads local paths |
| A TIFF or a NIfTI | Convert it first, with `ngff-zarr -i image.tif -o image.ome.zarr`: `write.py` reads OME-Zarr |
| Units | Both images must declare theirs. A store in micrometers against a file whose numbers mean millimeters will not register |
| An oblique grid | RFC-5 places an image by a scale and a translation: resample the pair onto an axis-aligned grid first |
| Little memory | The plan follows what it finds. A pair registered in less memory runs on a coarser grid, with a lower score |

## 2-D images

`register` takes single-channel 2-D images too, as OME-Zarr or as files, and gives back a 2-D transformation and a 2-D
moved image. In 2-D the transformation stays in ITK's `Transform.h5`: leave out the `--set`, which is refused there, and
`write.py` does not apply. On the middle plane of this organoid, on a GPU:

| Preset | Correlation (-0.06 before) | Time |
|---|---|---|
| `ConvexAdam_Composite` | 0.99 | 33 s |
| `FireANTs_SyN` | 0.97 | 28 s |
| `Generic_Rigid` | 0.90 | 10 s |
| `Generic_Rigid_BSpline` | 0.89 | 15 s |

## Larger images

The same commands hold at any size.

- **[`demo/`](demo/README.md):** two time points of a mouse embryo in light-sheet, read from a 9.3 TB public series. Three
  minutes on a GPU.
- **[Two mouse brains](media/videos/two-mouse-brains.mp4) (video):** ExaSPIM light-sheet, in OME-Zarr, up to 1.2 billion
  voxels on a laptop GPU.

## Going deeper

- [KonfAI](https://github.com/fideus-labs/KonfAI): the framework and IMPACT-Reg, its registration app.
- [ngff-zarr](https://github.com/fideus-labs/ngff-zarr): reading, writing and resampling OME-Zarr.
- [RFC-5](https://ngff.openmicroscopy.org/rfc/5/): coordinate systems and transformations in OME-Zarr.

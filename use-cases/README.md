# Use cases

The tutorial's steps on real data, one folder per case. Each folder has its README, its scripts and its figures.
Scenes are written and applied with [`steps/write.py`](../steps/write.py) and [`steps/apply.py`](../steps/apply.py),
and resampling through ITK transforms uses [`steps/resample.py`](../steps/resample.py).

| Case | Data | What it shows |
|---|---|---|
| [`mouse-embryo/`](mouse-embryo/README.md) | Two time points of a 9.3 TB light-sheet series, on the IDR | the four steps in one script, a displacement field, the scene in 3D Slicer |
| [`mouse-brain/`](mouse-brain/README.md) | Allen CCF and SmartSPIM templates on S3, 10 µm; an ExaSPIM template | reorienting from RFC-4 metadata, rigid against deformable, the field applied at 10 µm, 3D Slicer and napari |
| [`human-hemisphere/`](human-hemisphere/README.md) | A 7 T MRI and a 976 GB synchrotron scan of one hemisphere, on S3 | an 8 mm cube filled through an affine and a B-spline, reading 0.24 GB of the scan |

## Adding a case

1. Make a folder `use-cases/<name>/` with a `README.md`: where the data is, and the question.
2. Write a script that reads the data into local OME-Zarr stores in `use-cases/<name>/output/` (ignored by git), on the
   same axes and with units. `register` reads local stores, one channel each.
3. Run `impact-reg-konfai register` with `--fields-only` and `Transform:omezarr`, then `steps/write.py` and
   `steps/apply.py`. Put the commands in the README, with times and scores.
4. Add the pictures to `figures/`, and say what is still open.

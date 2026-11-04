# Use cases

The tutorial's four steps on real data, one folder per case. Each folder holds what the case needed beyond the
steps: how its data was read and put on common axes, the `register` commands that were run, the figures, and what is
still open. The scene is always written and applied with the tutorial's own `steps/write.py` and `steps/apply.py`.

| Case | Data | What it shows |
|---|---|---|
| [`mouse-brain/`](mouse-brain/README.md) | Allen CCF (STPT) and SmartSPIM templates, 10 µm, on S3; an ExaSPIM whole-head template | anonymous S3 reads, reorientation from RFC-4 orientations without interpolation, rigid against deformable, the field applied at 10 µm, the scene in 3D Slicer and napari |

## Adding a case

1. Make a folder, `use-cases/<name>/`, with a `README.md` that says where the data is and what the question was.
2. Put the reading in a script that writes local OME-Zarr stores to `use-cases/<name>/output/` (ignored by git), on the
   same axes and in declared units: `register` reads local stores, one channel each.
3. Run `impact-reg-konfai register` with `--fields-only` and `Transform:omezarr`, then `steps/write.py` and
   `steps/apply.py` as the tutorial does. Keep the commands in the README, with their times and scores.
4. Add the pictures that show the result to `figures/`, and say what remains open.

# A small cube from a huge scan

A 7 T MRI of a human hemisphere (fixed, 6 GB) and the same hemisphere scanned by synchrotron X-ray phase-contrast
tomography (moving, 976 GB at 20 µm), from the LINC project: subject Hb1,
[DANDI 001278](https://dandiarchive.org/dandiset/001278), CC-BY 4.0, read as OME-Zarr from DANDI's public S3.

The question is the resample, not the registration: choose a small cube in the MRI and fill it with the synchrotron
data at full resolution, through an affine and a B-spline, without reading the scan. ngff-zarr bounds where each
output block lands before reading anything, and reads only the chunks inside those bounds.

**[resample.ipynb](resample.ipynb)** runs it in about two and a half minutes, data read where it is:

| | |
|---|---|
| Output | an 8 mm cube of cortex, 399³ voxels at 20 µm |
| Read | 466 chunks of 1.9 million: 0.24 GB of the 976 GB scan |
| Time | 18 s for the cube |

```bash
pip install matplotlib   # beside the tutorial's requirements
jupyter lab use-cases/human-hemisphere/resample.ipynb
```

The same in one command, [steps/resample.py](../../steps/resample.py): two images and a sequence of ITK transforms,
applied in the order given, from the fixed image's points to the moving image's. The fixed image is a cube cut out of
the MRI; `--spacing` fills it at the scan's 20 µm.

```bash
cd use-cases/human-hemisphere
python crop_mri.py 36.0 46.4 92.4 8 output/mri_cube.ome.zarr    # centre (z, y, x) and size, mm
python ../../steps/resample.py output/mri_cube.ome.zarr s3://dandiarchive/zarr/6f11427f-ef86-42b8-9800-d3e09265c965 \
    bspline.h5 sform.h5 -o output/cube.ome.zarr --spacing 0.02007 \
    --storage-options '{"skip_signature": true, "region": "us-east-2"}'
```

- [`hemisphere.py`](hemisphere.py): the two images as lazy NgffImages in millimeters, the MRI's sform as an ITK affine,
  and the notebook's figures.
- [`bspline.h5`](bspline.h5), [`sform.h5`](sform.h5): the transformation, in two ITK files applied in that order. A
  cubic B-spline with control points every 30 mm (19 kB), then the MRI's sform, LINC's affine into the synchrotron's
  frame.
- [`crop_mri.py`](crop_mri.py): a cube of the MRI as a small local OME-Zarr, the fixed image of the command.
- [`make_bspline.py`](make_bspline.py): where the B-spline comes from. IMPACT-Reg's `Elastix_IMPACT_Static` on the MRI
  and the sform-placed scan at 1 mm (`final_grid_spacing=30`, about 3 min on a CPU), its field then fitted with a cubic
  ITK `BSplineTransform` (within 0.2 mm of it, median).

The two images have inverted contrasts: grey matter is bright in the MRI, white matter in the synchrotron. A correlation
says little here; the pictures show the alignment.

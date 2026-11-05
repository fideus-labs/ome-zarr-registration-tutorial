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

- [`hemisphere.py`](hemisphere.py): the two images as lazy NgffImages in millimeters, the MRI's sform as an ITK affine,
  and the notebook's figures.
- [`transform_bspline.h5`](transform_bspline.h5): the transformation, 19 kB. The MRI's sform (LINC's affine into the
  synchrotron's frame), then a cubic B-spline with control points every 30 mm.
- [`make_bspline.py`](make_bspline.py): where the B-spline comes from. IMPACT-Reg's `Elastix_IMPACT_Static` on the MRI
  and the sform-placed scan at 1 mm (`final_grid_spacing=30`, about 3 min on a CPU), its field then fitted with a cubic
  ITK `BSplineTransform` (within 0.2 mm of it, median).

The two images have inverted contrasts: grey matter is bright in the MRI, white matter in the synchrotron. A correlation
says little here; the pictures show the alignment.

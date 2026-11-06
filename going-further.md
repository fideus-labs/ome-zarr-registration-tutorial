# Going further

## Your own images

Any two images that should line up: two time points, two rounds, two samples, two modalities.

```bash
impact-reg-konfai register Generic_Rigid -f fixed.ome.zarr -m moving.ome.zarr -o output/mine --cpu 1 --fields-only \
    --set Predictor.outputs_dataset.DisplacementField.OutputDataset.dataset_filename=Transform:omezarr
python steps/write.py fixed.ome.zarr moving.ome.zarr output/mine/P000/Transform.ome.zarr output/mine.ozx
python steps/apply.py output/mine.ozx [fixed_labels.ome.zarr moving_labels.ome.zarr]
```

`write.py` takes an `affine` or a `displacements` field, and replaces an existing scene only with `--overwrite`.
`apply.py` computes one plane and, given two label images, the Dice of their masks.

Check first:

| Your data | What to do |
|---|---|
| Several channels or time points | Write the one you register to a store of its own, as [`get_data.py`](steps/get_data.py) and [`read_idr0044.py`](use-cases/mouse-embryo/read_idr0044.py) do |
| On a server or in a zip | Copy or unzip it first: `register` reads local paths |
| TIFF or NIfTI | Convert it first: `ngff-zarr -i image.tif -o image.ome.zarr` |
| Units | Both images must declare them. Micrometers against millimeters will not register |
| An oblique grid | The writers used here place a grid by a scale and a translation only. Resample the pair onto an axis-aligned grid first |
| Little memory | It still runs, on a coarser grid, with a lower score |

## Which way the transformation goes

The **fixed** image is the reference; the **moving** image is brought onto it. The transformation goes from the fixed
image to the moving one: for each point $x$ of the fixed image, it says where that point is in the moving image.

$$I_{\mathrm{aligned}}(x) = I_{\mathrm{moving}}\big(T_{\mathrm{fixed} \rightarrow \mathrm{moving}}(x)\big)$$

That is what a reader needs to draw the aligned image, and what the scene says: `input` is `fixed`, `output` is
`moving`. A point of the fixed image goes through $T$ as it is. A point of the moving image would need the inverse,
which `register` does not write.

Everything is in physical units and in z, y, x order: a point is three micrometer values, never voxel indices. So the
same transformation applies at every level of the pyramid.

## 2-D images

The same commands take single-channel 2-D images. `register` returns a 2-D transformation (a 2 × 3 `affine` for
`Generic_Rigid`, a field for the others), and `write.py` and `apply.py` work on it. On the middle plane of the
organoid:

| Preset | Correlation (-0.06 before) | Time |
|---|---|---|
| `ConvexAdam_Composite` | 0.99 | 22 s, GPU |
| `FireANTs_SyN` | 0.97 | 13 s, GPU |
| `Generic_Rigid_BSpline` | 0.91 | 11 s, CPU |
| `Generic_Rigid` | 0.90 | 9 s, CPU |

## What is lazy, and what is not

- **Step 1** reads only the chunks you ask for, from disk or from a server.
- **Step 2** reads both images whole, in regions that fit in memory. A pair too large for the device is registered on
  a coarser grid, then refined on tiles. A `displacements` field is written whole, one vector per fixed voxel.
- **Step 3** copies both images into the scene as they are. Nothing is resampled.
- **Step 4** is lazy: `resample` describes the moved image block by block, and each block reads only the chunks it
  needs. Nothing is computed until you ask for it.

## What the RFCs say

- **RFC-5** adds coordinate systems and transformations to OME-Zarr: the `affine` and `displacements` used here, and
  the scene that says what they connect. ngff-zarr reads and applies both; 3D Slicer opens the scene through
  SlicerOMEZarr. napari-ome-zarr 0.11 reads an `affine` written in the metadata, but not one stored as an array (as
  ngff-zarr 0.52 writes it), nor a field. [`tests/fixture/`](tests/fixture/) is a small scene to test a reader with.
- **RFC-9** is `.ozx`: the same store, zipped into one file. ngff-zarr reads and writes it.
- **RFC-8** (collections, a proposal) would let a scene point to images stored elsewhere instead of copying them. That
  is why `pair.ozx` is 42 MB today and not 4 kB.

## Links

- [KonfAI](https://github.com/fideus-labs/KonfAI): the framework, and IMPACT-Reg, its registration app.
- [ngff-zarr](https://github.com/fideus-labs/ngff-zarr): reading, writing and resampling OME-Zarr.
- [RFC-5](https://ngff.openmicroscopy.org/rfc/5/): coordinate systems and transformations in OME-Zarr.

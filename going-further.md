# Going further

## Your own pair

Any two images that should line up: two time points, two rounds, two samples, two modalities.

```bash
impact-reg-konfai register Generic_Rigid -f fixed.ome.zarr -m moving.ome.zarr -o output/mine --cpu 1 --fields-only \
    --set Predictor.outputs_dataset.DisplacementField.OutputDataset.dataset_filename=Transform:omezarr
python steps/write.py fixed.ome.zarr moving.ome.zarr output/mine/P000/Transform.ome.zarr output/mine.ozx
python steps/apply.py output/mine.ozx [fixed_labels.ome.zarr moving_labels.ome.zarr]
```

`write.py` takes the transformation in either RFC-5 form: the `affine` a linear preset writes, or the `displacements`
field of a deformable one, which it copies below the scene. It refuses to replace a scene unless you pass `--overwrite`.
`apply.py` computes one plane and, given two label images, the Dice of their masks through the same transformation.

What to check first:

| Your data | What to do |
|---|---|
| Several channels or time points | Register one image: write the channel or the time point to a store of its own, as [`steps/get_data.py`](steps/get_data.py) and [`demo/read_idr0044.py`](demo/read_idr0044.py) do |
| On a server or in a zip | Copy or unzip it first: `register` reads local paths |
| A TIFF or a NIfTI | Convert it first, with `ngff-zarr -i image.tif -o image.ome.zarr`: `write.py` reads OME-Zarr |
| Units | Both images must declare theirs. A store in micrometers against a file whose numbers mean millimeters will not register |
| An oblique grid | RFC-5 can place a grid by any affine, but the writers used here place one by a scale and a translation, and a field on a rotated grid gets no `displacements` entry: resample the pair onto an axis-aligned grid first |
| Little memory | The plan follows what it finds. A pair registered in less memory runs on a coarser grid, with a lower score |

## Fixed, moving, and which way the transformation goes

The **fixed** image is the reference; the **moving** image is the one brought onto it. The transformation `register`
writes goes from the fixed image to the moving one: for each point $x$ of the fixed image, where that point is in the
moving image,

$$I_{\mathrm{aligned}}(x) = I_{\mathrm{moving}}\big(T_{\mathrm{fixed} \rightarrow \mathrm{moving}}(x)\big).$$

That is what a reader needs to draw the aligned image, and what the scene says: `input` is `fixed`, `output` is
`moving`. Points of the fixed image, landmarks, go through $T$ as they are; a point of the moving image would need the
inverse, which `register` does not write.

Each image has an **intrinsic** coordinate system, its physical space in its own unit (micrometers here), and its
pyramid levels map onto it by a scale and a translation per level. Everything in the scene is in those units and in
the axes' order, z, y, x: a point is three micrometer values, never three voxel indices, and the transformation is the
same whatever level of the pyramid you apply it to.

## 2-D images

The same commands take single-channel 2-D images: `register` gives back a 2-D RFC-5 transformation (a 2 × 3 `affine`
for `Generic_Rigid`, a field for the others) and a 2-D moved image, and `write.py` and `apply.py` work on them. On the
middle plane of this organoid:

| Preset | Correlation (-0.06 before) | Time |
|---|---|---|
| `ConvexAdam_Composite` | 0.99 | 22 s, GPU |
| `FireANTs_SyN` | 0.97 | 13 s, GPU |
| `Generic_Rigid_BSpline` | 0.91 | 11 s, CPU |
| `Generic_Rigid` | 0.90 | 9 s, CPU |

## What is lazy, and what is not

- **Step 1** reads the chunks you ask for, from your disk or from a server alike. `get_data.py`, run once before it,
  materializes the two rounds out of the Zenodo plate: the registration reads local files.
- **Step 2** reads the two images whole. IMPACT-Reg streams them in regions within the memory it has, and a pair too
  large for the device is registered on a coarser grid, then refined on native tiles. A `displacements` field is
  written whole, one vector per voxel of the fixed image.
- **Step 3** copies the two images into the scene, as they are, and a field below it. The scene is a copy of the data,
  not a resampled one.
- **Step 4** is lazy: `resample` describes the moving image on the fixed grid, and computes the blocks you ask for,
  reading the chunks of the moving image and of the field those blocks need. The whole image is never materialized
  unless you ask for all of it.

## Larger images

The same commands hold at any size.

- **[`demo/`](demo/README.md):** two time points of a mouse embryo in light-sheet, read from a 9.3 TB public series. Three
  minutes on a GPU.
- **[Two mouse brains](media/videos/two-mouse-brains.mp4) (video):** ExaSPIM light-sheet, in OME-Zarr, up to 1.2 billion
  voxels on a laptop GPU.
- **[`use-cases/`](use-cases/README.md):** real cases, one folder each, with their scripts and figures; the first is the Allen
  CCF and SmartSPIM templates, from S3 to 3D Slicer.

## One file, and what the RFCs say

- **RFC-5** gives OME-Zarr its coordinate systems and transformations: the `affine` and the `displacements` field of
  this tutorial, and a scene that names what they connect. ngff-zarr reads and applies both today. napari-ome-zarr
  0.11 opens the scene and shows the moving image through its `affine`, the two rounds aligned, but not yet through a
  `displacements` field. Other readers are catching up, and [`tests/fixture/`](tests/fixture/) is a small scene to
  check one against.
- **RFC-9** is the `.ozx` form: the scene's store, zipped into one file. Readers support it to different degrees;
  ngff-zarr reads and writes it, and the unzipped store is the same thing.
- **RFC-8**, collections, is a proposal: a scene could then refer to images that live elsewhere instead of copying
  them below it. Today a scene holds its images, which is why `pair.ozx` is 42 MB and not 4 kB.

## Going deeper

- [KonfAI](https://github.com/fideus-labs/KonfAI): the framework and IMPACT-Reg, its registration app.
- [ngff-zarr](https://github.com/fideus-labs/ngff-zarr): reading, writing and resampling OME-Zarr.
- [RFC-5](https://ngff.openmicroscopy.org/rfc/5/): coordinate systems and transformations in OME-Zarr.

# Step 3. Write, and read back

**Goal:** write the registration as OME-Zarr, both images and the transformation between them in one file, and check
what a reader finds in it.

## Run it

```bash
impact-reg-konfai scene --transform output/registration/P000/Transform.h5 \
    -f output/R0.ome.zarr -m output/R1.ome.zarr -o output/pair.ozx
```

## What you should see

```text
[ImpactReg] scene output/pair.ozx (affine)
```

`pair.ozx` is one file, a zipped OME-Zarr 0.6 store (RFC-9):

```text
pair.ozx                 43 MB
├── zarr.json            the scene, and the transformation
├── fixed/               R0, with its pyramid
└── moving/              R1, with its pyramid
```

## What just happened

- **The transformation is now metadata (RFC-5).** A rigid result is an affine: 12 numbers, in place of the 437 MB of
  `Transform.h5`.
- **It says what it connects:** from the coordinate system of `fixed` to the one of `moving`.
- **It is in the images' own unit,** here micrometers, in the axis order z, y, x.

## Read it back

```bash
python steps/read_scene.py
```

```text
fixed: 50 x 680 x 535 voxels, 3 levels
moving: 50 x 680 x 535 voxels, 3 levels
transformation: affine, from fixed to moving
[[  1.    -0.01   0.02   0.47]
 [  0.01   1.     0.   -10.02]
 [ -0.02  -0.     1.    36.83]]
```

Nothing is computed: this is the file's metadata, read by ngff-zarr through
[`NgffScene.from_ome_zarr`](read_scene.py). Any OME-Zarr 0.6 reader finds the same thing in `zarr.json`:

```json
{"coordinateTransformations": [{
  "type": "affine",
  "input":  {"path": "fixed",  "name": "intrinsic"},
  "output": {"path": "moving", "name": "intrinsic"},
  "affine": [[...], [...], [...]]}]}
```

The last column reads directly: between the two rounds, the organoid moved 37 µm along x and 10 µm along y.

## A deformable result

A deformable preset gives an RFC-5 `displacements` field, stored beside the images as float32. It need not be as fine
as the image: `--factor` stores it that many times coarser. With `ConvexAdam_Composite` on this pair:

| `--factor` | `pair.ozx` | Nuclei overlap (Dice) |
|---|---|---|
| 1 | 223 MB | 0.94 |
| 4 | 46 MB | 0.94 |

**Next: [Step 4. Apply](4-apply.md)**

# Step 3. Write

**Goal:** write the registration as OME-Zarr: both images and the transformation between them, in one file.

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

Look at it, in `zarr.json`:

```bash
unzip -p output/pair.ozx zarr.json | python -c "import json, sys; print(json.dumps(json.load(sys.stdin)['attributes']['ome']['scene'], indent=1))"
```

```json
{"coordinateTransformations": [{
  "type": "affine",
  "input":  {"path": "fixed",  "name": "intrinsic"},
  "output": {"path": "moving", "name": "intrinsic"},
  "affine": [[ 0.9997, -0.0101,  0.0242,   0.47],
             [ 0.0101,  0.9999,  0.0015, -10.02],
             [-0.0242, -0.0012,  0.9997,  36.83]]}]}
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

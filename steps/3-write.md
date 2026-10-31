# Step 3. Write, and read back

**Goal:** with ngff-zarr alone, write both images and the transformation between them in one OME-Zarr 0.6 file, and check
what a reader finds in it.

## Run it

```bash
python steps/write.py
```

## What you should see

```text
Scene: output/pair.ozx
```

`pair.ozx` is one file, a zipped OME-Zarr 0.6 store (RFC-9):

```text
pair.ozx                        135 MB
├── zarr.json                   the scene: what the transformation connects
├── fixed/                      R0, with its pyramid
├── moving/                     R1, with its pyramid
└── coordinateTransformations/
    └── registration/           the field of step 2
```

## What just happened

- **The transformation was OME-Zarr already.** Step 2 wrote it as an RFC-5 `displacements` field. It is copied as it
  is: an ordinary OME-Zarr image, whose first axis holds the components (dz, dy, dx), in micrometers.
- **The scene says what it connects:** from the coordinate system of `fixed` to the one of `moving`.
- **No registration tool is needed from here on.** This step and the next one only use ngff-zarr.

The part that matters in [`write.py`](write.py):

```python
# The transformation is an OME-Zarr image already: it goes below the scene, first.
nz.to_ome_zarr(f"{STORE}/{FIELD}", nz.from_ome_zarr(TRANSFORM), version="0.6")

# The scene names what it connects: from the coordinates of the fixed image to those of the moving one.
registration = Displacements(
    path=FIELD,
    interpolation="linear",
    input=CoordinateSystemIdentifier(path="fixed", name="intrinsic"),
    output=CoordinateSystemIdentifier(path="moving", name="intrinsic"),
)
images = {"fixed": nz.from_ome_zarr(FIXED), "moving": nz.from_ome_zarr(MOVING)}
NgffScene(images=images, coordinateTransformations=[registration]).to_ome_zarr(STORE, overwrite=False)

# One file: the same store, zipped (RFC-9).
nz.write_store_to_zip(STORE, SCENE, version="0.6")
```

## Read it back

```bash
python steps/read_scene.py
```

```text
fixed: 50 x 680 x 535 voxels, 3 levels
moving: 50 x 680 x 535 voxels, 3 levels
transformation: displacements, from fixed to moving
its field: coordinateTransformations/registration, 3 x 50 x 680 x 535
at the centre of the image: dz 1.1, dy -9.8, dx 36.4 micrometers
```

This is the file's metadata, read by ngff-zarr through [`NgffScene.from_ome_zarr`](read_scene.py), plus one vector of
the field. Any OME-Zarr 0.6 reader finds the same thing in `zarr.json`:

```json
{"scene": {"coordinateTransformations": [{
  "type": "displacements",
  "path": "coordinateTransformations/registration",
  "interpolation": "linear",
  "input":  {"path": "fixed",  "name": "intrinsic"},
  "output": {"path": "moving", "name": "intrinsic"}}]}}
```

The last line of the output reads directly: between the two rounds, the centre of the organoid moved 36 µm along x and
10 µm along y.

## The size of the transformation

| Preset | `Transform.h5` | `Transform.ome.zarr` | `pair.ozx` |
|---|---|---|---|
| `Generic_Rigid` | 437 MB | 90 MB | 135 MB |
| `ConvexAdam_Composite` | 437 MB | 170 MB | 218 MB |

The field is stored as float32, on the fixed image's grid.

**Next: [Step 4. Apply](4-apply.md)**

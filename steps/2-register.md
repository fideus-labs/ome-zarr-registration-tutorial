# Step 2. Register

**Goal:** align round R1 onto round R0, with one command.

## Run it

```bash
impact-reg-konfai register Generic_Rigid \
    -f output/R0.ome.zarr -m output/R1.ome.zarr -o output/registration --cpu 4
```

With a GPU, replace `--cpu 4` by `--gpu 0`.

## What you should see

```text
[ImpactReg] Registration completed in 15 s
  Preset:    Generic_Rigid (Generic Rigid)
  Transform: output/registration/P000/Transform.h5
  Moved:     output/registration/P000/Moved.ome.zarr
  Record:    output/registration/register.json
```

The first run takes longer: it downloads the preset and the elastix binary.

## What just happened

- **`-f` is the fixed image, `-m` the moving one.** The result maps points of the fixed image to the moving image.
- **The images were read from their stores.** The command measures the GPU and the memory it has. A pair too large for
  them is registered on a coarser grid, then refined on native tiles, with the same command.
- **The preset's lengths are in voxels,** so it needs no tuning for a voxel of 0.2 µm or of 2 mm.
- **You get three things:** `Transform.h5` (the transformation, as ITK writes it), `Moved.ome.zarr` (the moving image,
  resampled) and `register.json` (what ran, with which versions).

`Moved.ome.zarr` is the resampled copy this tutorial wants to do without. Steps 3 and 4 show how.

## Try another preset

The engine is just a name. `impact-reg-konfai list` shows them all, and `impact-reg-konfai show <preset>` what each one
does and what it needs.

| Preset | Engine | Time on this pair | Correlation | Nuclei overlap | Runs on |
|---|---|---|---|---|---|
| `Generic_Rigid` | elastix, rigid | 15 s, CPU | 0.89 | 0.91 | any machine |
| `Generic_Rigid_BSpline` | elastix, rigid then B-spline | 1 min 15, CPU | 0.89 | 0.78 | any machine |
| `ConvexAdam_Composite` | ConvexAdam on MIND features | 42 s, GPU | 0.99 | 0.94 | Linux and Windows, no macOS package |
| `FireANTs_SyN` | FireANTs, diffeomorphic | 3 min 16, GPU | 0.99 | 0.93 | a GPU: over 50 min on a CPU |

Deformable is not always better: here, the B-spline matches the image as well as the rigid does, and moves the nuclei
further from each other.

The scores come from [step 4](4-apply.md): `python steps/apply.py your_scene.ozx`. Correlation starts at -0.06, and the
overlap at 0.

**Next: [Step 3. Write, and read back](3-write.md)**

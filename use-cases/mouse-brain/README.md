# Mouse-brain templates, registered through OME-Zarr

The four steps of the tutorial on a case brought to the OME-Zarr Hackathon 2026 by the Allen Institute: the Allen CCF
atlas and two light-sheet templates, on S3, to be registered onto one another. Everything below runs from the root of
this repository, in the tutorial's environment; the outputs land in `use-cases/mouse-brain/output/`.

## The data

| Template | Store | Format | Voxel | Levels | Axes (intrinsic) |
|---|---|---|---|---|---|
| CCF, STPT 2020 | `s3://allen-atlas-assets/templates/allen-adult-mouse-stpt-template/2020/template.ome.zarr` | OME-Zarr 0.6 | 10 µm, mm | 10, 25 µm | z A→P, y D→V, x L→R |
| SmartSPIM LCA 2024-05 | `s3://allen-atlas-assets/templates/allen-adult-mouse-spim-lca-template/2024-05/template.ome.zarr` | OME-Zarr 0.6 | 10 µm, mm | 10 to 100 µm | z R→L, y A→P, x D→V |
| ExaSPIM CCFv4 2026-09 | `s3://aind-scratch-data/exaspim-ccfv4-template/20260930-2055/template.ome.zarr` | OME-Zarr 0.5 | 40 × 30 × 30 µm | 4 | none declared; a whole head |

- All three read anonymously. With ngff-zarr, the `https://…s3.amazonaws.com` form makes obstore look for EC2
  credentials and hang; the `s3://` form with `storage_options={"skip_signature": True, "region": "us-west-2"}` opens
  in 3 s.
- The two Allen stores carry RFC-5: an `intrinsic` system with anatomical orientations on each axis, and a sequence
  onto a `mm RAS` system. Their intrinsic axes differ: a permutation and a flip.

## 1. Read, and reorient from the metadata

```bash
python use-cases/mouse-brain/read_templates.py      # about 1 GB over S3, ten minutes
python use-cases/mouse-brain/reorient_exaspim.py    # the ExaSPIM, by hand: it declares no orientation
```

`read_templates.py` reads one level of each (25 µm for CCF and SmartSPIM, 60 µm for ExaSPIM) into local stores, and
puts the SmartSPIM template on the CCF's axes by the permutation and flips its RFC-4 orientations dictate:
`transpose [1, 2, 0]`, flip x. No interpolation. The ExaSPIM store declares nothing, so `reorient_exaspim.py` reads
its axes off its middle planes (a head in profile on a y plane, nose along +x, dorsal along −z) and does the same by
hand; the left-right handedness is assumed.

## 2. Register SmartSPIM onto the CCF

```bash
impact-reg-konfai register Generic_Rigid -f use-cases/mouse-brain/output/ccf.ome.zarr -m use-cases/mouse-brain/output/smartspim.ome.zarr \
    -o use-cases/mouse-brain/output/rigid --cpu 8 --fields-only \
    --set Predictor.outputs_dataset.DisplacementField.OutputDataset.dataset_filename=Transform:omezarr
# the same with FireANTs_SyN --gpu 0 -o use-cases/mouse-brain/output/fireants, and ConvexAdam_Composite
```

## 3 and 4. Write the scene, apply, look

```bash
python steps/write.py use-cases/mouse-brain/output/ccf.ome.zarr use-cases/mouse-brain/output/smartspim.ome.zarr \
    use-cases/mouse-brain/output/fireants/P000/Transform.ome.zarr use-cases/mouse-brain/output/fireants.ozx --overwrite
python steps/apply.py use-cases/mouse-brain/output/fireants.ozx
python use-cases/mouse-brain/pictures.py use-cases/mouse-brain/output/fireants.ozx    # overlays and checkerboards, three planes
python use-cases/mouse-brain/moved_10um.py                                   # the field applied at 10 µm, on the S3 stores
```

Correlation with the CCF on the three middle planes (before: coronal −0.38, horizontal 0.01):

| Preset | Time | Coronal | Horizontal | Sagittal | Output |
|---|---|---|---|---|---|
| `Generic_Rigid` | 48 s, CPU | 0.39 | 0.15 | 0.24 | an affine, almost a 1.5 mm translation per axis: the reorientation was right. The SmartSPIM brain is larger than the CCF, which a rigid cannot fix |
| `ConvexAdam_Composite` | 4 min 27 s, GPU, a tiled pass | 0.43 | 0.12 | 0.20 | a 718 MB field, `convexadam.ozx` 935 MB. The cortex outline follows the CCF's; olfactory bulbs and cerebellar folia are left behind |
| `FireANTs_SyN` | 7 min 07 s, GPU, a tiled pass | 0.44 | 0.36 | 0.49 | a 724 MB field, `fireants.ozx` 941 MB. Its affine stage takes the scale difference, SyN the rest: the best of the three on every plane |

The correlation is a rough guide here: STPT and light-sheet contrasts differ inside the brain, so even a perfect
alignment scores well below 1. The checkerboards are the judge.

**Scales.** The registration ran at 25 µm. The transformations are in millimeters, so they apply to any level:
`moved_10um.py` applies the FireANTs field to the 10 µm level of both stores, read from S3 and reoriented the same
way, and writes `smartspim_on_ccf_10um.ome.zarr`, 1320 × 800 × 1140 voxels, 2.2 GB, in 90 s.

## In 3D Slicer and napari

```bash
Slicer --python-script use-cases/mouse-brain/slicer_before_after.py   # before and after: the FireANTs transformation applied in Slicer
Slicer --python-script use-cases/mouse-brain/slicer_view.py           # the stores, the moved copies, the transformations
python use-cases/mouse-brain/napari_scene.py use-cases/mouse-brain/output/rigid.ome.zarr use-cases/mouse-brain/output/napari_rigid.png --keep
```

With the SlicerOMEZarr extension, `rigid.ome.zarr` and `fireants.ome.zarr` also open as scenes: the fixed image stays,
the moving one hangs under the transformation, a linear transform for the affine and a grid transform for the field,
applied as stored. `napari_scene.py` shows a scene in napari, the moving image resampled lazily by ngff-zarr,
for the affine and the field alike.

A detail on frames: ngff-zarr's RFC-4 helper knows the six human orientations only, and `dorsal-to-ventral` is not one
of them, so SlicerOMEZarr falls back to its assumed orientation, identity direction, for these stores. That is the frame
KonfAI registered in, so the ITK transformations written by `slicer_before_after.py` apply as they are; Slicer's A/P/S/I
labels do not mean the mouse's axes here.

## Figures

| | |
|---|---|
| ![Rigid, before and after](figures/rigid_summary.png) | ![Rigid, ConvexAdam, and before](figures/summary_coronal.png) |

- `figures/rigid_planes.png`, `convexadam_planes.png`, `fireants_planes.png`: overlays and checkerboards on the three
  middle planes, one per preset.
- `figures/fireants_10um_coronal.png`: the FireANTs field applied at 10 µm on the S3 stores.
- `figures/slicer_before_red.png`, `slicer_after_*.png`: 3D Slicer, the FireANTs transformation applied in Slicer.
- `figures/napari_rigid.png`, `napari_fireants.png`: `rigid.ome.zarr` and `fireants.ome.zarr` in napari.
- `figures/exaspim_axes_mid_*.png`, `exaspim_rigid_planes.png`: the ExaSPIM template on the CCF's axes, and its rigid
  onto the CCF.

## ExaSPIM, still open

A whole head, in a frame with no declared orientation. Reoriented by hand, its rigid onto the CCF runs; a brain mask
is the next step before a deformable means anything.

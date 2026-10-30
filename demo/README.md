# Demo: a mouse embryo at scale

Two time points, 8 h 20 min apart, of one mouse embryo filmed in light-sheet
([McDole et al., Cell 2018](https://doi.org/10.1016/j.cell.2018.09.031)). The series is 9.3 TB on the
[IDR](https://idr.openmicroscopy.org/); this reads two time points of one channel, at one level, and nothing else.

```bash
bash demo/run.sh          # level 3 (69 million voxels) of time points 150 and 250, on GPU 0
```

| Step | Result, on a laptop GPU |
|---|---|
| Read | 8 s per time point |
| Register (`ConvexAdam_Composite`) | 2 min 16 s, correlation over the volume 0.30 -> 0.70 |
| Write (`--factor 4`) | 15 MB, against 1.6 GB for `Transform.h5` |
| Apply | one plane computed, from `pair.ozx`, in about a second |

The whole run takes about 5 minutes and 16 GB of memory. The score depends on the memory: under 22 GB, the coarse pass
holds fewer voxels and the correlation falls to 0.59.

<img src="../media/embryo.gif" width="340" alt="The two time points of the embryo, before and after registration">

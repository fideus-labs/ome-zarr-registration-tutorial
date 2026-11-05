"""The LINC Hb1 left hemisphere on DANDI 001278 (CC-BY 4.0): a 7 T MRI (fixed) and its synchrotron HiP-CT scan
(moving), read where they are on S3, and the figures of the notebook.

Both images are NgffImages in (z, y, x) order and millimeters, so ITK sees one physical space for both. The MRI's
sform (NIfTI voxel -> synchrotron world, mm) is the affine between them.
"""

import logging

import dask
import dask.array
import itk
import matplotlib.pyplot as plt
import ngff_zarr as nz
import numpy as np
from dask.optimization import cull
from matplotlib.patches import Rectangle

logging.getLogger("ngff_zarr").setLevel(logging.ERROR)

S3 = {"skip_signature": True, "region": "us-east-2"}
MRI = "s3://dandiarchive/zarr/97691c51-846e-4777-b2e5-68ff09b4357b"  # FLASH T2*, space-XPCT, NIfTI-Zarr, mm
XPCT = "s3://dandiarchive/zarr/6f11427f-ef86-42b8-9800-d3e09265c965"  # HiP-CT overview, 20.07 um, axes (x, y, z)

# The MRI's sform at level 0: NIfTI voxel (i, j, k) -> synchrotron world (x, y, z), mm.
SFORM = np.array(
    [
        [-1.42408116e-02, -2.47345753e-02, -1.16636083e-01, 1.73587799e02],
        [-6.24938216e-03, 1.17063932e-01, -2.43768562e-02, 4.54313469e01],
        [-1.18715368e-01, -3.09704128e-03, 1.55453552e-02, 1.71731781e02],
    ]
)


def pyramid(url):
    return nz.from_ngff_zarr(url, storage_options=S3)


def mri(level):
    """The MRI at ``level``, (z, y, x) in mm. Nothing is read."""
    image = pyramid(MRI).images[level]
    return nz.NgffImage(
        data=image.data[0],
        dims=["z", "y", "x"],
        name="mri",
        scale={a: image.scale[a] for a in "zyx"},
        translation={a: image.translation[a] for a in "zyx"},
    )


def xpct(level):
    """The synchrotron scan at ``level``, viewed in (z, y, x) order and mm. Nothing is read."""
    image = pyramid(XPCT).images[level]
    return nz.NgffImage(
        data=image.data.transpose([image.dims.index(a) for a in "zyx"]),
        dims=["z", "y", "x"],
        name="xpct",
        scale={a: image.scale[a] / 1000 for a in "zyx"},
        translation={a: image.translation[a] / 1000 for a in "zyx"},
    )


def sform():
    """The sform as an ITK affine from MRI points to synchrotron points, (x, y, z) in mm."""
    voxel = np.array([pyramid(MRI).images[0].scale[a] for a in "xyz"])
    affine = itk.AffineTransform[itk.D, 3].New()
    affine.SetMatrix(itk.matrix_from_array(SFORM[:, :3] / voxel))
    affine.SetTranslation(SFORM[:, 3])
    return affine


def grid(centre_mm, size_mm, spacing_mm, chunks=128):
    """A cubic output grid in the MRI's frame: geometry only, its pixels are never read."""
    n = int(round(size_mm / spacing_mm))
    corner = np.asarray(centre_mm) - spacing_mm * (n - 1) / 2
    return nz.NgffImage(
        data=dask.array.zeros((n, n, n), dtype=np.uint16, chunks=chunks),
        dims=["z", "y", "x"],
        scale=dict.fromkeys("zyx", spacing_mm),
        translation=dict(zip("zyx", corner.tolist())),
        name="cube",
    )


def chunks_read(moved, moving):
    """The chunks of the scan's own array that computing ``moved`` reads: (x, y, z) chunk indices."""
    layers = {name for name in moving.data.dask.layers if name != moving.data.name}
    culled, _ = cull(dict(moved.data.__dask_graph__()), list(dask.core.flatten(moved.data.__dask_keys__())))
    return np.array(sorted(key[1:] for key in culled if isinstance(key, tuple) and len(key) == 4 and key[0] in layers))


# ----------------------------------------------------------------------------------------------------- figures


def _scaled(image, where=None):
    values = image[where] if where is not None and where.any() else image
    low, high = np.percentile(values, (1, 99.5))
    return np.clip((image - low) / max(high - low, 1e-6), 0, 1)


def _overlay(green, magenta):
    return np.stack([magenta, green, magenta], -1)


def _off(ax, title):
    ax.set_xticks([]), ax.set_yticks([])
    ax.set_title(title, color="white", fontsize=12)


def _figure(columns, width=4.6, height=4.2):
    fig, axes = plt.subplots(1, columns, figsize=(width * columns, height), facecolor="black")
    return fig, np.atleast_1d(axes)


def show_alignment(transform, mri_level=3, xpct_level=5):
    """The middle sagittal plane: the synchrotron without a transform, through the affine, through the affine and
    the B-spline, over the MRI (green); then how far the B-spline moves each point of the MRI."""
    fixed = mri(mri_level)
    m = np.asarray(fixed.data, dtype=np.float32)
    tissue = m > 0.1 * np.percentile(m, 99)
    identity = itk.IdentityTransform[itk.D, 3].New()
    steps = [("no transform", identity), ("affine (the sform)", sform()), ("affine + B-spline", transform)]
    k = m.shape[1] // 2
    fig, axes = _figure(4)
    for ax, (name, t) in zip(axes, steps, strict=False):
        x = np.asarray(nz.resample(t, fixed, xpct(xpct_level)).data, dtype=np.float32)
        ax.imshow(_overlay(_scaled(m[:, k], tissue[:, k]), _scaled(x[:, k], tissue[:, k] & (x[:, k] > 0))))
        _off(ax, name)
    bspline = transform.GetNthTransform(1)
    z, x = np.meshgrid(np.arange(m.shape[0]), np.arange(m.shape[2]), indexing="ij")
    points = np.stack(
        [
            fixed.translation["x"] + x * fixed.scale["x"],
            np.full(x.shape, fixed.translation["y"] + k * fixed.scale["y"]),
            fixed.translation["z"] + z * fixed.scale["z"],
        ],
        -1,
    ).reshape(-1, 3)
    moved = np.array([bspline.TransformPoint(p.tolist()) for p in points])
    shift = np.linalg.norm(moved - points, axis=1).reshape(x.shape)
    ax = axes[3]
    ax.imshow(_scaled(m[:, k]), cmap="gray")
    shown = ax.imshow(np.where(tissue[:, k], shift, np.nan), cmap="magma", alpha=0.75)
    _off(ax, "B-spline displacement (mm)")
    bar = fig.colorbar(shown, ax=ax, fraction=0.04)
    bar.ax.tick_params(colors="white")
    fig.tight_layout()
    return fig


def show_cube_in_mri(cube, mri_level=2):
    """The MRI's three planes through the cube's centre, the cube drawn on them."""
    fixed = mri(mri_level)
    m = np.asarray(fixed.data, dtype=np.float32)
    lo = np.array([cube.translation[a] for a in "zyx"])
    hi = lo + np.array(cube.data.shape) * np.array([cube.scale[a] for a in "zyx"])
    centre = (lo + hi) / 2
    scale, origin = np.array([fixed.scale[a] for a in "zyx"]), np.array([fixed.translation[a] for a in "zyx"])
    index = np.round((centre - origin) / scale).astype(int)
    fig, axes = _figure(3)
    for axis, ax in enumerate(axes):
        plane = np.take(m, index[axis], axis=axis)
        rows, cols = [a for a in range(3) if a != axis]
        extent = [
            origin[cols],
            origin[cols] + scale[cols] * plane.shape[1],
            origin[rows] + scale[rows] * plane.shape[0],
            origin[rows],
        ]
        ax.imshow(_scaled(plane), cmap="gray", extent=extent)
        ax.add_patch(
            Rectangle((lo[cols], lo[rows]), hi[cols] - lo[cols], hi[rows] - lo[rows], fill=False, ec="red", lw=2)
        )
        _off(ax, f"MRI, plane {'zyx'[axis]} = {centre[axis]:.0f} mm")
    fig.tight_layout()
    return fig


def show_reads(transform, cube, moved, moving, overview_level=4, zoom_level=2):
    """Where the cube lands in the scan, and the chunks the resample reads there: the whole hemisphere, then a zoom
    with the scan's chunk grid. The cube's faces, carried through the transform, are the red outline."""
    read = chunks_read(moved, moving)
    source = pyramid(XPCT).images[0]
    chunk_mm = np.array(source.data.chunksize) * source.scale["x"] / 1000  # (x, y, z)
    voxel_mm = source.scale["x"] / 1000
    # The cube's faces in the scan: a lattice on each face, each point carried through the transform.
    n = 30
    lo = np.array([cube.translation[a] for a in "xyz"])
    hi = lo + np.array(cube.data.shape[::-1]) * np.array([cube.scale[a] for a in "xyz"])
    u = np.linspace(0, 1, n)
    faces = []
    for axis in range(3):
        for side in (0.0, 1.0):
            a, b = np.meshgrid(u, u, indexing="ij")
            f = np.zeros((n * n, 3))
            others = [i for i in range(3) if i != axis]
            f[:, axis] = side
            f[:, others[0]], f[:, others[1]] = a.ravel(), b.ravel()
            faces.append(lo + f * (hi - lo))
    landed = np.array([transform.TransformPoint(p.tolist()) for p in np.concatenate(faces)])  # (x, y, z) mm
    z_mm = landed[:, 2].mean()
    k = int(z_mm // chunk_mm[2])
    near = np.abs(landed[:, 2] - z_mm) < chunk_mm[2] / 2

    overview = pyramid(XPCT).images[overview_level]
    level_mm = overview.scale["x"] / 1000
    plane = np.asarray(overview.data[:, :, int(z_mm / level_mm)], dtype=np.float32)  # (x, y)
    fig, axes = _figure(2, width=7.2, height=6.6)
    extent = [0, plane.shape[0] * level_mm, plane.shape[1] * level_mm, 0]
    in_plane = read[read[:, 2] == k]
    for ax, zoom in zip(axes, (False, True), strict=True):
        ax.imshow(_scaled(plane.T), cmap="gray", extent=extent)
        for ci, cj, _ in in_plane:
            ax.add_patch(
                Rectangle(
                    (ci * chunk_mm[0], cj * chunk_mm[1]),
                    chunk_mm[0],
                    chunk_mm[1],
                    fc=(1, 0.8, 0, 0.35),
                    ec=(1, 0.8, 0, 0.9),
                    lw=0.6 if zoom else 0.3,
                )
            )
        ax.plot(landed[near, 0], landed[near, 1], ".", color="red", ms=1.5)
        if zoom:
            x0, x1 = in_plane[:, 0].min() * chunk_mm[0], (in_plane[:, 0].max() + 1) * chunk_mm[0]
            y0, y1 = in_plane[:, 1].min() * chunk_mm[1], (in_plane[:, 1].max() + 1) * chunk_mm[1]
            pad = 2 * chunk_mm[0]
            # The zoom's background from a finer level, just that window of it.
            fine = pyramid(XPCT).images[zoom_level]
            fine_mm = fine.scale["x"] / 1000
            i0, i1 = int((x0 - pad) / fine_mm), int((x1 + pad) / fine_mm)
            j0, j1 = int((y0 - pad) / fine_mm), int((y1 + pad) / fine_mm)
            window = np.asarray(fine.data[i0:i1, j0:j1, int(z_mm / fine_mm)], dtype=np.float32)
            ax.images[0].remove()
            ax.imshow(
                _scaled(window.T),
                cmap="gray",
                extent=[i0 * fine_mm, i1 * fine_mm, j1 * fine_mm, j0 * fine_mm],
                zorder=0,
            )
            ax.set_xlim(x0 - pad, x1 + pad), ax.set_ylim(y1 + pad, y0 - pad)
            for edge in np.arange(np.floor((x0 - pad) / chunk_mm[0]), np.ceil((x1 + pad) / chunk_mm[0]) + 1):
                ax.axvline(edge * chunk_mm[0], color="white", lw=0.3, alpha=0.4)
            for edge in np.arange(np.floor((y0 - pad) / chunk_mm[1]), np.ceil((y1 + pad) / chunk_mm[1]) + 1):
                ax.axhline(edge * chunk_mm[1], color="white", lw=0.3, alpha=0.4)
        title = (
            f"zoom: the scan's chunks ({chunk_mm[0]:.2f} mm), those read in yellow"
            if zoom
            else f"the whole scan, plane z = {z_mm:.0f} mm: the cube in red"
        )
        _off(ax, title)
    fig.tight_layout()
    total = source.data.size * source.data.dtype.itemsize
    got = len(read) * int(np.prod(source.data.chunksize)) * source.data.dtype.itemsize
    print(
        f"{len(read)} chunks of {np.prod(source.data.numblocks):,} read: {got / 1e9:.2f} GB of {total / 1e9:.0f} GB "
        f"({got / total:.1e}); voxel {voxel_mm * 1000:.2f} um"
    )
    return fig


def show_cube(mri_cube, xpct_cube, size_mm, inset_mm=2.0, inset_at=(0.62, 0.38)):
    """The cube's middle plane: the MRI, the synchrotron at full resolution, both, and a zoom of the synchrotron at
    ``inset_at`` (row, column, as fractions of the plane)."""
    k = xpct_cube.shape[0] // 2
    a, b = _scaled(mri_cube[k]), _scaled(xpct_cube[k])
    fig, axes = _figure(4)
    for ax, image, name in zip(
        axes, (a, b, _overlay(a, b)), ("MRI, 0.12 mm", "synchrotron, 20 um", "both (MRI green)"), strict=False
    ):
        ax.imshow(image, cmap="gray")
        _off(ax, name)
    n = b.shape[0]
    side = int(n * inset_mm / size_mm)
    r0, c0 = int(n * inset_at[0]) - side // 2, int(n * inset_at[1]) - side // 2
    axes[1].add_patch(Rectangle((c0, r0), side, side, fill=False, ec="yellow", lw=1.5))
    axes[3].imshow(_scaled(xpct_cube[k][r0 : r0 + side, c0 : c0 + side].astype(np.float32)), cmap="gray")
    _off(axes[3], f"zoom, {inset_mm:g} mm")
    fig.tight_layout()
    return fig

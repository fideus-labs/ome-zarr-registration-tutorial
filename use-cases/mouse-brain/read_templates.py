"""Read the three Allen mouse-brain templates from S3, anonymously, at one level each, into local stores.

    python use-cases/mouse-brain/read_templates.py

The SmartSPIM template comes out reoriented onto the CCF's anatomical axes, by a permutation and flips of its array
read from the RFC-5 orientations of the two stores: no interpolation. Each store gets a middle-plane picture.
"""

import sys
from pathlib import Path

import dask.array as da
import ngff_zarr as nz
import numpy as np
from PIL import Image

ANON = {"skip_signature": True, "region": "us-west-2"}
TEMPLATES = {
    "ccf": ("s3://allen-atlas-assets/templates/allen-adult-mouse-stpt-template/2020/template.ome.zarr", 1),
    "smartspim": ("s3://allen-atlas-assets/templates/allen-adult-mouse-spim-lca-template/2024-05/template.ome.zarr", 1),
    "exaspim": ("s3://aind-scratch-data/exaspim-ccfv4-template/20260930-2055/template.ome.zarr", 1),
}
OUTPUT = Path(__file__).resolve().parent / "output"
OPPOSITE = {
    "left-to-right": "right-to-left",
    "anterior-to-posterior": "posterior-to-anterior",
    "dorsal-to-ventral": "ventral-to-dorsal",
    "superior-to-inferior": "inferior-to-superior",
}
OPPOSITE |= {b: a for a, b in OPPOSITE.items()}


def orientations(image):
    return {
        axis: o.value.value if hasattr(o.value, "value") else str(o.value)
        for axis, o in (image.axes_orientations or {}).items()
    }


def reoriented(image, target_image):
    """``image`` with its axes permuted and flipped so that each one runs as ``target_image``'s do: no resampling."""
    source, target = orientations(image), orientations(target_image)
    order, flips = [], []
    for axis in image.dims:  # the target's axes, in its order
        wanted = target[axis]
        for candidate, direction in source.items():
            if direction == wanted or direction == OPPOSITE[wanted]:
                order.append(image.dims.index(candidate))
                flips.append(direction != wanted)
                break
        else:
            sys.exit(f"no axis of {source} runs along {wanted}")
    data = image.data.transpose(order)
    data = data[tuple(slice(None, None, -1) if flip else slice(None) for flip in flips)]
    dims = list(image.dims)
    return (
        nz.NgffImage(
            data=data,
            dims=dims,
            scale={dims[i]: image.scale[image.dims[j]] for i, j in enumerate(order)},
            translation={d: 0.0 for d in dims},
            axes_units={dims[i]: image.axes_units[image.dims[j]] for i, j in enumerate(order)},
            axes_orientations=dict(target_image.axes_orientations),  # the axes now run as the target's do
        ),
        order,
        flips,
    )


def picture(image, path):
    z = image.data.shape[0] // 2
    plane = np.asarray(image.data[z]).astype(float)
    low, high = np.percentile(plane, (1, 99.5))
    Image.fromarray((np.clip((plane - low) / max(high - low, 1e-6), 0, 1) * 255).astype(np.uint8)).save(path)


if __name__ == "__main__":
    OUTPUT.mkdir(exist_ok=True)
    images = {}
    for name, (url, level) in TEMPLATES.items():
        multiscales = nz.from_ngff_zarr(url, storage_options=ANON)
        image = multiscales.images[level]
        images[name] = image
        print(
            f"{name}: level {level}, {image.dims} {image.data.shape} {image.data.dtype}, {', '.join(f'{k} {v:.4g} {image.axes_units[k]}' for k, v in image.scale.items())}, orientations {orientations(image) or 'none'}"
        )

    moving, order, flips = reoriented(images["smartspim"], images["ccf"])
    print(
        f"smartspim onto ccf's axes: transpose {order}, flip {flips} -> {moving.data.shape}, orientations {orientations(moving)}"
    )

    for name, image in (("ccf", images["ccf"]), ("smartspim", moving), ("exaspim", images["exaspim"])):
        image = nz.NgffImage(
            data=da.asarray(image.data).rechunk((64, 128, 128)),
            dims=list(image.dims),
            scale=dict(image.scale),
            translation={d: 0.0 for d in image.dims},
            axes_units=dict(image.axes_units),
            axes_orientations=image.axes_orientations,
        )
        store = OUTPUT / f"{name}.ome.zarr"
        nz.to_ngff_zarr(store, nz.to_multiscales(image, scale_factors=[2, 4]), version="0.5")
        picture(nz.from_ngff_zarr(store).images[0], OUTPUT / f"{name}_z.png")
        print(f"wrote {store.name}: {image.data.shape}")

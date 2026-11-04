"""Overlays and checkerboards of a scene, on the three middle planes: python use-cases/mouse-brain/pictures.py SCENE.ozx [TILE]"""

import sys
from pathlib import Path

import ngff_zarr as nz
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "steps"))  # the tutorial's common.py
from common import ncc, scene_fields  # noqa: E402
from PIL import Image, ImageDraw, ImageFont

SCENE = sys.argv[1]
TILE = int(sys.argv[2]) if len(sys.argv) > 2 else 48
name = Path(SCENE).stem

scene = nz.NgffScene.from_ome_zarr(SCENE)
transformation = scene.coordinateTransformations[0]
fixed, moving = scene.images["fixed"].images[0], scene.images["moving"].images[0]
moved = nz.resample(transformation, fixed, moving, fields=scene_fields(SCENE, transformation))


def scaled(plane):
    low, high = np.percentile(plane, (1, 99.5))
    return np.clip((plane.astype(float) - low) / max(high - low, 1e-6), 0, 1)


def overlay(f, m):
    return (np.stack([m, f, m], axis=-1) * 255).astype(np.uint8)


def checkerboard(f, m):
    rows, cols = np.indices(f.shape) // TILE
    board = np.where((rows + cols) % 2 == 0, f, m)
    return (np.stack([board] * 3, axis=-1) * 255).astype(np.uint8)


panels = []
for axis, label in ((0, "coronal (z)"), (1, "horizontal (y)"), (2, "sagittal (x)")):
    index = [slice(None)] * 3
    index[axis] = fixed.data.shape[axis] // 2
    f, m = np.asarray(fixed.data[tuple(index)]), np.asarray(moved.data[tuple(index)])
    score = ncc(f, m)
    f, m = scaled(f), scaled(m)
    panels.append(
        (f"{label}, correlation {score:.2f}", Image.fromarray(overlay(f, m)), Image.fromarray(checkerboard(f, m)))
    )

width = max(o.width for _, o, _ in panels) * 2 + 20
height = sum(o.height for _, o, _ in panels) + 40 * len(panels) + 30
out = Image.new("RGB", (width, height), (255, 255, 255))
draw = ImageDraw.Draw(out)
try:
    font, small = ImageFont.truetype("DejaVuSans.ttf", 17), ImageFont.truetype("DejaVuSans.ttf", 14)
except Exception:
    font = small = ImageFont.load_default()
y = 0
for label, over, board in panels:
    draw.text(
        (6, y + 10),
        f"{name}, {label}: overlay (green fixed, magenta moved) and checkerboard",
        fill=(0, 0, 0),
        font=font,
    )
    out.paste(over, (0, y + 40))
    out.paste(board, (over.width + 20, y + 40))
    y += over.height + 40
draw.text(
    (6, height - 24),
    f"{transformation.type} from {transformation.input.path} to {transformation.output.path}",
    fill=(60, 60, 60),
    font=small,
)
path = Path(SCENE).with_name(f"{name}_planes.png")
out.save(path)
print(path, out.size)

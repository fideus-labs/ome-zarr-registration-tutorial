"""Show an OME-Zarr 0.6 scene in napari: the fixed image, and the moving one resampled lazily through the scene's
transformation. Saves a screenshot, and stays open with --keep.

python napari_scene.py SCENE OUT.png [--keep]
"""

import sys
from pathlib import Path

import napari
import ngff_zarr as nz
from qtpy.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "steps"))  # the tutorial's common.py
from common import scene_fields, view  # noqa: E402

scene_path, out = sys.argv[1], sys.argv[2]
scene = nz.NgffScene.from_ome_zarr(scene_path)
T = scene.coordinateTransformations[0]
fixed = scene.images[T.input.path].images[0]
moved = nz.resample(T, fixed, scene.images[T.output.path].images[0], fields=scene_fields(scene_path, T))
viewer = view(fixed, moved)
viewer.reset_view()
for _ in range(20):
    QApplication.processEvents()
viewer.screenshot(out, canvas_only=True)
print("screenshot:", out, flush=True)
if "--keep" in sys.argv:
    napari.run()
else:
    viewer.close()

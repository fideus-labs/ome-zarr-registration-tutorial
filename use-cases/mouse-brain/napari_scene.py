"""Open an OME-Zarr 0.6 scene with napari-ome-zarr, list what napari got, save a screenshot, and stay open with --keep.

python napari_scene.py SCENE_DIR OUT.png [--keep]
"""

import sys

import napari
import numpy as np
from qtpy.QtWidgets import QApplication

scene, out = sys.argv[1], sys.argv[2]
viewer = napari.Viewer(show=True, title=f"napari-ome-zarr: {scene}")
layers = viewer.open(scene, plugin="napari-ome-zarr")
print(f"{len(layers)} layer(s):")
for layer in layers:
    data = layer.data[0] if isinstance(layer.data, list) else layer.data
    print(
        f"  {layer.name}: {type(layer).__name__} shape {data.shape} scale {np.round(layer.scale, 4).tolist()} translate {np.round(layer.translate, 3).tolist()}"
    )
    print(f"    affine:\n{np.array2string(np.asarray(layer.affine.affine_matrix), precision=3, suppress_small=True)}")
if len(viewer.layers) >= 2:
    viewer.layers[0].colormap = "green"
    viewer.layers[1].colormap = "magenta"
    for layer in viewer.layers:
        layer.blending = "additive"
if viewer.dims.ndim >= 3:
    viewer.dims.set_point(0, (viewer.dims.range[0][0] + viewer.dims.range[0][1]) / 2)
viewer.reset_view()
for _ in range(20):
    QApplication.processEvents()
viewer.screenshot(out, canvas_only=True)
print("screenshot:", out, flush=True)
if "--keep" in sys.argv:
    napari.run()
else:
    viewer.close()

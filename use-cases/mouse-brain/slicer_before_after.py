"""Before and after FireANTs in 3D Slicer: Slicer --python-script use-cases/mouse-brain/slicer_before_after.py

The CCF is the background, the reoriented SmartSPIM the foreground at 50 %. "Before" is the SmartSPIM as it sits;
"after" is the same volume with the FireANTs transformation applied to it in Slicer (Transforms module: untick or
tick `FireANTs` on `smartspim` to go back and forth). The script saves the three slice views in both states to output/.
"""

from pathlib import Path

import slicer

OUTPUT = Path(__file__).resolve().parent / "output"


def load(name):
    node = slicer.util.loadNodeFromFile(str(OUTPUT / name), "OMEZarr", {})
    node.SetName(name.replace(".ome.zarr", ""))
    return node


def capture(state):
    slicer.app.processEvents()
    for view in ("Red", "Yellow", "Green"):
        widget = slicer.app.layoutManager().sliceWidget(view)
        widget.sliceView().forceRender()
        widget.sliceView().grab().save(str(OUTPUT / f"slicer_{state}_{view.lower()}.png"))


ccf = load("ccf.ome.zarr")
moving = load("smartspim.ome.zarr")
transform = slicer.util.loadTransform(str(OUTPUT / "fireants.h5"))
transform.SetName("FireANTs")

layout = slicer.app.layoutManager()
layout.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
slicer.util.setSliceViewerLayers(background=ccf, foreground=moving, foregroundOpacity=0.5, fit=True)
for composite in slicer.util.getNodesByClass("vtkMRMLSliceCompositeNode"):
    composite.SetLinkedControl(True)
capture("before")

moving.SetAndObserveTransformNodeID(transform.GetID())
capture("after")
print("before and after captured in", OUTPUT)

"""Open the registration in 3D Slicer, through the SlicerOMEZarr extension: Slicer --python-script use-cases/mouse-brain/slicer_view.py

Loads the CCF (background), the reoriented SmartSPIM (foreground, as it sits before registration) and, when present,
the SmartSPIM moved onto the CCF by FireANTs (foreground) and the ITK forms of the transformations. The stores carry
their RFC-4 orientations, which the extension turns into direction cosines: the volumes land in anatomical space.
"""

from pathlib import Path

import slicer

OUTPUT = Path(__file__).resolve().parent / "output"


def load(name, **properties):
    node = slicer.util.loadNodeFromFile(str(OUTPUT / name), "OMEZarr", properties)
    node.SetName(name.replace(".ome.zarr", ""))
    return node


ccf = load("ccf.ome.zarr")
moving = load("smartspim.ome.zarr")
moved = load("smartspim_on_ccf.ome.zarr") if (OUTPUT / "smartspim_on_ccf.ome.zarr").exists() else None
# The same at 10 um, 1.2 billion voxels, when use-cases/mouse-brain/moved_10um.py has run: the OME-Zarr module loads the level that fits.
if (OUTPUT / "smartspim_on_ccf_10um.ome.zarr").exists():
    load("smartspim_on_ccf_10um.ome.zarr")

# The transformations, as KonfAI wrote them: fixed to moving, in the frame of the stores' voxel grids (identity
# direction, origin 0, millimeters). Apply one to `smartspim` in the Transforms module and it lands on `ccf`, as long
# as Slicer places the stores in that same frame (see the README).
for name in ("rigid.h5", "fireants.h5"):
    if (OUTPUT / name).exists():
        transform = slicer.util.loadTransform(str(OUTPUT / name))
        transform.SetName(name.removesuffix(".h5"))

layout = slicer.app.layoutManager()
layout.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
slicer.util.setSliceViewerLayers(background=ccf, foreground=moved or moving, foregroundOpacity=0.5, fit=True)
for composite in slicer.util.getNodesByClass("vtkMRMLSliceCompositeNode"):
    composite.SetLinkedControl(True)
print(
    "CCF in the background, SmartSPIM moved by FireANTs in the foreground at 50 %; the transforms are in the Transforms module."
)

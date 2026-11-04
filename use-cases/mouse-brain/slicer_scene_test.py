"""Open OME-Zarr 0.6 scenes through SlicerOMEZarr (PR #15) and say what Slicer made of them.

    Slicer --additional-module-paths <SlicerOMEZarr>/OMEZarr --python-script slicer_scene_test.py SCENE [SCENE...]

For each scene: the nodes, the transform hierarchy, the transform classes and their directions, and a screenshot
of the Red view with the second image over the first.
"""

import sys
import time
from pathlib import Path

import slicer
import vtk

scenes = [a for a in sys.argv[1:] if a.endswith(".zarr")]
OUT = Path(scenes[0]).parent if scenes else Path(".")


def describe(scene):
    slicer.mrmlScene.Clear(False)
    print(f"\n=== {scene}", flush=True)
    t = time.time()
    try:
        node = slicer.util.loadNodeFromFile(scene, "OMEZarr", {})
    except Exception as error:
        print(f"LOAD FAILED: {type(error).__name__}: {error}", flush=True)
        return
    print(f"loaded in {time.time() - t:.1f} s; first node: {node.GetName() if node else None}", flush=True)
    for volume in slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode"):
        image = volume.GetImageData()
        parent = volume.GetParentTransformNode()
        chain = []
        while parent is not None:
            chain.append(parent.GetName())
            parent = parent.GetParentTransformNode()
        print(
            f"  volume {volume.GetName()}: {image.GetDimensions() if image else None}, spacing {tuple(round(s, 4) for s in volume.GetSpacing())}, transforms up to world: {chain or 'none'}",
            flush=True,
        )
    for transform in slicer.util.getNodesByClass("vtkMRMLTransformNode"):
        kind = transform.GetClassName()
        inner = transform.GetTransformToParent()
        parent = transform.GetParentTransformNode()
        text = f"  transform {transform.GetName()} ({kind}): to-parent is {inner.GetClassName() if inner else None}"
        if transform.IsLinear():
            m = vtk.vtkMatrix4x4()
            transform.GetMatrixTransformToParent(m)
            text += ", matrix to parent " + str([[round(m.GetElement(i, j), 3) for j in range(4)] for i in range(3)])
        elif inner is not None and inner.IsA("vtkGeneralTransform"):
            parts = [
                inner.GetConcatenatedTransform(i).GetClassName()
                for i in range(inner.GetNumberOfConcatenatedTransforms())
            ]
            text += f", stages {parts}"
        text += f", parent {parent.GetName() if parent else 'world'}"
        print(text, flush=True)
    volumes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
    if len(volumes) >= 2:
        slicer.util.setSliceViewerLayers(background=volumes[0], foreground=volumes[1], foregroundOpacity=0.5, fit=True)
    elif volumes:
        slicer.util.setSliceViewerLayers(background=volumes[0], fit=True)
    slicer.app.processEvents()
    for view in ("Red", "Green"):
        widget = slicer.app.layoutManager().sliceWidget(view)
        widget.sliceView().forceRender()
        path = OUT / f"slicer_scene_{Path(scene).stem.replace('.ome', '')}_{view.lower()}.png"
        widget.sliceView().grab().save(str(path))
    print(f"  screenshots in {OUT}", flush=True)


print("OMEZarr module:", slicer.modules.omezarr.path, flush=True)
slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
for scene in scenes:
    describe(scene)
print("done", flush=True)
slicer.util.exit(0)

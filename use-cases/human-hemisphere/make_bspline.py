"""Where transform_bspline.h5 comes from: python make_bspline.py

The registration only has to give a credible B-spline; the notebook is about the resample.

1. The synchrotron scan, placed on the MRI's grid by the sform (1 mm, a few MB read), and the MRI, as NIfTI.
2. IMPACT-Reg's elastix B-spline between them (Elastix_IMPACT_Static, control points every 30 voxels, about 3 min
   on a CPU), which writes its result as a displacement field.
3. That field fitted with a cubic ITK BSplineTransform, control points every 30 mm, by separable least squares
   (within 0.2 mm of the field, median), and composed after the sform: transform_bspline.h5.
"""

import subprocess
from pathlib import Path

import itk
import ngff_zarr as nz
import numpy as np
import SimpleITK as sitk
from hemisphere import mri, sform, xpct

OUT = Path("output")
OUT.mkdir(exist_ok=True)

# 1. The pair IMPACT-Reg registers, on one grid
fixed = mri(3)
for name, data in (
    ("fixed", np.asarray(fixed.data, dtype=np.float32)),
    ("moving", np.asarray(nz.resample(sform(), fixed, xpct(5)).data, dtype=np.float32)),
):
    image = sitk.GetImageFromArray(data)
    image.SetSpacing([fixed.scale[a] for a in "xyz"])
    image.SetOrigin([fixed.translation[a] for a in "xyz"])
    sitk.WriteImage(image, str(OUT / f"{name}.nii.gz"))

# 2. The registration
subprocess.run(
    [
        "impact-reg-konfai",
        "register",
        "Elastix_IMPACT_Static",
        "-f",
        "fixed.nii.gz",
        "-m",
        "moving.nii.gz",
        "-o",
        "registration",
        "--cpu",
        "1",
        "--set",
        "final_grid_spacing=30",
    ],
    cwd=OUT,
    check=True,
)
field_transform = itk.transformread(str(OUT / "registration" / "P000" / "Transform.h5"))[0]

# 3. The field as a cubic B-spline. ITK's BSplineTransform: control points on a grid of mesh + 3 per axis, starting
# one spacing before the domain's origin; a point at continuous grid index u moves by sum_j beta3(u - j) c_j.
field = field_transform.GetDisplacementField()
displacement = itk.array_from_image(field).astype(np.float64)  # (z, y, x, 3), components (x, y, z), mm
origin, step, size = np.array(itk.origin(field)), np.array(itk.spacing(field)), np.array(itk.size(field))
mesh = np.maximum(1, np.round((size - 1) * step / 30.0).astype(int))
spacing = (size - 1) * step / mesh
grid_origin, grid_size = origin - spacing, mesh + 3


def beta3(t):
    t = np.abs(t)
    return np.where(t < 1, 2 / 3 - t**2 + t**3 / 2, np.where(t < 2, (2 - t) ** 3 / 6, 0.0))


def basis(axis):
    u = (origin[axis] + np.arange(size[axis]) * step[axis] - grid_origin[axis]) / spacing[axis]
    return beta3(u[:, None] - np.arange(grid_size[axis])[None, :])


Px, Py, Pz = (np.linalg.pinv(basis(axis)) for axis in range(3))
coefficients = np.einsum("az,by,cx,zyxd->abcd", Pz, Py, Px, displacement)


def parameters(values):
    out = itk.OptimizerParameters[itk.D](len(values))
    for i, value in enumerate(values):
        out[i] = float(value)
    return out


bspline = itk.BSplineTransform[itk.D, 3, 3].New()
bspline.SetFixedParameters(parameters([*grid_size, *grid_origin, *spacing, *np.eye(3).ravel()]))
bspline.SetParameters(parameters([v for d in range(3) for v in coefficients[..., d].ravel()]))  # x fastest; x, y, z

transform = itk.CompositeTransform[itk.D, 3].New()
transform.AddTransform(sform())
transform.AddTransform(bspline)  # applied first: MRI point -> B-spline -> sform -> synchrotron point
itk.transformwrite([transform], "transform_bspline.h5")
print(f"transform_bspline.h5: the sform, then a B-spline of {bspline.GetNumberOfParameters()} parameters")

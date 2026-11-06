#!/usr/bin/env bash
# The tutorial's four steps on two time points of a mouse embryo.
#   bash use-cases/mouse-embryo/run.sh [LEVEL] [T_FIXED] [T_MOVING]
set -euo pipefail
LEVEL=${1-3}; FIXED=${2-150}; MOVING=${3-250}
OUT=use-cases/mouse-embryo/output; F=$OUT/t$FIXED.ome.zarr; M=$OUT/t$MOVING.ome.zarr
mkdir -p $OUT

# 1. Read one time point and one channel each, from the public series
python use-cases/mouse-embryo/read_idr0044.py "$FIXED" "$LEVEL" "$F"
python use-cases/mouse-embryo/read_idr0044.py "$MOVING" "$LEVEL" "$M"

# 2. Register: write the transformation only, in OME-Zarr
impact-reg-konfai register ConvexAdam_Composite -f "$F" -m "$M" -o $OUT/registration --gpu "${GPU-0}" --fields-only \
    --set Predictor.outputs_dataset.DisplacementField.OutputDataset.dataset_filename=Transform:omezarr

# 3. Write both images and the field in one scene
python steps/write.py "$F" "$M" $OUT/registration/P000/Transform.ome.zarr $OUT/pair.ozx --overwrite

# 4. Apply it to one plane, from the scene
python steps/apply.py $OUT/pair.ozx

# Look in 3D Slicer (needs the SlicerOMEZarr extension)
if [ -n "${SLICER-}" ]; then
    "$SLICER" --python-code "slicer.util.loadNodeFromFile('$PWD/$OUT/pair.ome.zarr', 'OMEZarr')"
else
    echo "To see it in 3D Slicer: drag $OUT/pair.ome.zarr onto it"
fi

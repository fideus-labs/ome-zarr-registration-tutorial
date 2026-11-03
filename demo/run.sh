#!/usr/bin/env bash
# The tutorial's steps, on two time points of a mouse embryo: bash demo/run.sh [LEVEL] [T_FIXED] [T_MOVING]
set -euo pipefail
LEVEL=${1-3}; FIXED=${2-150}; MOVING=${3-250}
OUT=output/embryo; F=$OUT/t$FIXED.ome.zarr; M=$OUT/t$MOVING.ome.zarr
mkdir -p $OUT

# 1. Read: one time point and channel each, from the public series, into a local store
python demo/read_idr0044.py "$FIXED" "$LEVEL" "$F"
python demo/read_idr0044.py "$MOVING" "$LEVEL" "$M"

# 2. Register: the transformation alone (--fields-only: no resampled copy of the moving image), in OME-Zarr
impact-reg-konfai register ConvexAdam_Composite -f "$F" -m "$M" -o $OUT/registration --gpu "${GPU-0}" --fields-only \
    --set Predictor.outputs_dataset.DisplacementField.OutputDataset.dataset_filename=Transform:omezarr

# 3. Write: the two images and the field in one scene (the field is copied below the scene, the images beside it)
python steps/write.py "$F" "$M" $OUT/registration/P000/Transform.ome.zarr $OUT/pair.ozx --overwrite

# 4. Apply: one plane, computed from the scene; nothing else is written
python steps/apply.py $OUT/pair.ozx

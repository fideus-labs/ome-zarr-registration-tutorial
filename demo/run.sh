#!/usr/bin/env bash
# The tutorial's steps, on two time points of a mouse embryo: bash demo/run.sh [LEVEL] [T_FIXED] [T_MOVING]
set -euo pipefail
LEVEL=${1-3}; FIXED=${2-150}; MOVING=${3-250}
OUT=output/embryo; F=$OUT/t$FIXED.ome.zarr; M=$OUT/t$MOVING.ome.zarr
mkdir -p $OUT

# 1. Read
python demo/read_idr0044.py "$FIXED" "$LEVEL" "$F"
python demo/read_idr0044.py "$MOVING" "$LEVEL" "$M"

# 2. Register
impact-reg-konfai register ConvexAdam_Composite -f "$F" -m "$M" -o $OUT/registration --gpu "${GPU-0}" \
    --set Predictor.outputs_dataset.DisplacementField.OutputDataset.dataset_filename=Transform:omezarr

# 3. Write
python steps/write.py "$F" "$M" $OUT/registration/P000/Transform.ome.zarr $OUT/pair.ozx

# 4. Apply
python steps/apply.py $OUT/pair.ozx

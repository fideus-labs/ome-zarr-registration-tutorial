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
impact-reg-konfai register ConvexAdam_Composite -f "$F" -m "$M" -o $OUT/registration --gpu "${GPU-0}"

# 3. Write, the field 4 times coarser than the image
impact-reg-konfai scene --transform $OUT/registration/P000/Transform.h5 -f "$F" -m "$M" -o $OUT/pair.ozx --factor 4

# 4. Apply
python steps/apply.py $OUT/pair.ozx

#!/bin/bash

. ./apikey.sh

source activate testenv1

# batch submission

# Greater Manchester
regions="
E08000001 \
E08000002 \
E08000003 \
E08000004 \
E08000005 \
E08000006 \
E08000007 \
E08000008 \
E08000009 \
E08000010 \
"

qsub_params="-l h_rt=4:0:0"

for region in $regions; do
  export REGION=$region
  qsub $qsub_params run.sh
done


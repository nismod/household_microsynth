#!/bin/bash

# single job submission

# TODO pass (and check) args from cmd line

region=W06000016
resolution=OA11

. ./apikey.sh

source activate testenv1

qsub_params="-l h_rt=8:0:0"

outfile="hh_"$region"_"$resolution".csv"
if [ ! -f $outfile ]; then
  export REGION=$region
  echo Submitting job for $REGION
  qsub $qsub_params run.sh
  sleep 10
else
  echo $region done, not resubmitting
fi


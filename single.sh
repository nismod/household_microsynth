#!/bin/bash

# single job submission - args from cmd line
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <region(s)> <resolution>"
  echo   e.g. $0 E09000001 OA11
  exit 1
fi

region=$1
resolution=$2

if [ ! -f ~/apikey.sh ]; then
  echo "api key not found. Please specify your Nomisweb API key in ~/apikey.sh, e.g.:"
  echo "export NOMIS_API_KEY=0x0123456789abcdef0123456789abcdef01234567"
  exit 1
fi
. ~/apikey.sh

# appropriate conda env should be activated manually
#source activate default
if [ "$CONDA_DEFAULT_ENV" == "" ]; then
  echo Error, no conda env activated
  exit 1
fi

qsub_params="-l h_rt=8:0:0"

outfile="hh_"$region"_"$resolution".csv"
if [ ! -f $outfile ]; then
  export REGION=$region
  echo Submitting job for $REGION
  qsub -o ./logs -e ./logs $qsub_params run.sh
else
  echo $region done, not resubmitting
fi


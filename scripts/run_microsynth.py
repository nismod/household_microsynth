#!/usr/bin/env python3

# run script for Household microsynthesis

import numpy as np
import pandas as pd
import ukcensusapi.Nomisweb as Api
import household_microsynth.microsynthesis as hhms

# Set country or local authority/ies here
region = "City of London"
# Set resolution LA/MSOA/LSOA/OA
resolution = Api.Nomisweb.LSOA


(LC4402, LC4404, LC4405, LC4408, LC1105EW, KS401EW) = hhms.getCensusData(region, resolution)

print(LC4402.head(5))
print(LC4404.head(5))
print(LC4405.head(5))
print(LC4408.head(5))
print(LC1105EW.head(5))
print(KS401EW.head(5))





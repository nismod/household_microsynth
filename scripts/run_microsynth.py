#!/usr/bin/env python3

# Disable "Invalid constant name"
# pylint: disable=C0103

# run script for Household microsynthesis

import numpy as np
import pandas as pd
import ukcensusapi.Nomisweb as Api
import household_microsynth.Microsynthesis as Microsynthesiser

# Set country or local authority/ies here
region = "City of London"
# Set resolution LA/MSOA/LSOA/OA
resolution = Api.Nomisweb.LSOA

# The microsynthesis makes use of the following tables:
# LC4402EW - Accommodation type by type of central heating in household by tenure
# LC4404EW - Tenure by household size by number of rooms
# LC4405EW - Tenure by household size by number of bedrooms
# LC4408EW - Tenure by number of persons per bedroom in household by household type
# LC1105EW - Residence type by sex by age
# KS401EW - Dwellings, household spaces and accommodation type
# QS420EW - Communal establishment management and type - Communal establishments
# QS421EW - Communal establishment management and type - People

# specify cache directory
microsynthesiser = Microsynthesiser.Microsynthesis("./")

(LC4402, LC4404, LC4405, LC4408, LC1105EW, KS401EW) = microsynthesiser.get_census_data(region, resolution)

# Do some basic checks on totals
total_occ_dwellings = sum(LC4402.OBS_VALUE)

#stopifnot(sum(tenurePeopleRooms$OBS_VALUE) == totalOccDwellings)
#stopifnot(sum(tenurePeopleBeds$OBS_VALUE) == totalOccDwellings)
#stopifnot(sum(tenurePpbComp$OBS_VALUE) == totalOccDwellings)
#stopifnot(sum(unoccupied[unoccupied$CELL==5,]$OBS_VALUE) == totalOccDwellings)

total_population = sum(LC1105EW.OBS_VALUE)
total_dwellings = sum(KS401EW.OBS_VALUE)
#total_communal = sum(communalDetail$Count)

#occPopLBound = sum(tenurePeopleRooms$C_SIZHUK11*tenurePeopleRooms$OBS_VALUE)
#householdPopulation = sum(communal[communal$C_RESIDENCE_TYPE == 1,]$OBS_VALUE)
#communalPopulation = sum(communal[communal$C_RESIDENCE_TYPE == 2,]$OBS_VALUE)

print("Dwellings: ", str(total_dwellings))
print("Occupied households: " + str(total_occ_dwellings))
print("Unoccupied dwellings: " + str(total_dwellings- total_occ_dwellings))
#print("Communal residences: " + str(total_communal))

#print("Total population: ", totalPopulation)
#print("Population in occupied households: ", householdPopulation)
#print("Population in communal residences: ", communalPopulation)
#print("Population lower bound from occupied households: ", occPopLBound)
#print("Occupied household population underestimate: ", householdPopulation - occPopLBound)

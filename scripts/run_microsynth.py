#!/usr/bin/env python3

# run script for Household microsynthesis

import sys
import time
import numpy as np
import pandas as pd
import humanleague
import ukcensusapi.Nomisweb as Api
import household_microsynth.microsynthesis as Microsynthesiser
import household_microsynth.utils as Utils

assert humanleague.version() == 1
CACHE_DIR = "./cache"

# # Set country or local authority/ies here
# REGION = "City of London"
# #REGION = "Newcastle upon Tyne"
# # Set resolution LA/MSOA/LSOA/OA
# RESOLUTION = Api.Nomisweb.OA

# The microsynthesis makes use of the following tables:
# LC4402EW - Accommodation type by type of central heating in household by tenure
# LC4404EW - Tenure by household size by number of rooms
# LC4405EW - Tenure by household size by number of bedrooms
# LC4408EW - Tenure by number of persons per bedroom in household by household type
# LC1105EW - Residence type by sex by age
# KS401EW - Dwellings, household spaces and accommodation type
# QS420EW - Communal establishment management and type - Communal establishments
# QS421EW - Communal establishment management and type - People
# TODO
# LC4202EW - Tenure by car or van availability by ethnic group of Household Reference Person (HRP)
# LC4601EW - Tenure by economic activity by age - Household Reference Persons
# TODO: differentiate between purpose-built and converted flats?

def main(region, resolution):

  # start timing
  start_time = time.time()

  # specify cache directory
  microsynthesiser = Microsynthesiser.Microsynthesis(CACHE_DIR)

  print("Microsynthesis region: ", region)
  print("Microsynthesis resolution: ", resolution)
  # convert input string to enum
  resolution = microsynthesiser.Area[resolution]
  # get the census data
  microsynthesiser.get_census_data(region, resolution)

  # TODO move into microsynthesiser generate indices
  type_index = microsynthesiser.lc4402.C_TYPACCOM.unique()
  type_index = np.append(type_index, 6) # this value denotes communal
  tenure_index = microsynthesiser.lc4402.C_TENHUK11.unique()
  ch_index = microsynthesiser.lc4402.C_CENHEATHUK11.unique()
  ppb_index = microsynthesiser.lc4408.C_PPBROOMHEW11.unique()
  comp_index = microsynthesiser.lc4408.C_AHTHUK11.unique()
  comp_index = np.append(comp_index, 6) # this value denotes unoccupied

  # Do some basic checks on totals
  total_occ_dwellings = sum(microsynthesiser.lc4402.OBS_VALUE)
  print(total_occ_dwellings)
  assert sum(microsynthesiser.lc4404.OBS_VALUE) == total_occ_dwellings
  assert sum(microsynthesiser.lc4405.OBS_VALUE) == total_occ_dwellings
  assert sum(microsynthesiser.lc4408.OBS_VALUE) == total_occ_dwellings
  assert sum(microsynthesiser.ks401[microsynthesiser.ks401.CELL == 5].OBS_VALUE) == total_occ_dwellings

  total_dwellings = sum(microsynthesiser.lc1105.OBS_VALUE)
  total_households = sum(microsynthesiser.ks401.OBS_VALUE)
  total_communal = sum(microsynthesiser.communal.OBS_VALUE)
  total_dwellings = total_households + total_communal

  occ_pop_lbound = sum(microsynthesiser.lc4404.C_SIZHUK11 * microsynthesiser.lc4404.OBS_VALUE)
  household_dwellings = sum(microsynthesiser.lc1105[microsynthesiser.lc1105.C_RESIDENCE_TYPE == 1].OBS_VALUE)
  communal_dwellings = sum(microsynthesiser.lc1105[microsynthesiser.lc1105.C_RESIDENCE_TYPE == 2].OBS_VALUE)

  print("Households: ", total_households)
  print("Occupied households: ", total_occ_dwellings)
  print("Unoccupied dwellings: ", total_households - total_occ_dwellings)
  print("Communal residences: ", total_communal)
  print("Dwellings: ", total_dwellings)

  print("Total dwellings: ", total_dwellings)
  print("Population in occupied households: ", household_dwellings)
  print("Population in communal residences: ", communal_dwellings)
  print("Population lower bound from occupied households: ", occ_pop_lbound)
  print("Occupied household dwellings underestimate: ", household_dwellings - occ_pop_lbound)

  # TODO move this code into the Microsynthesise class...

  all_areas = microsynthesiser.lc4402.GEOGRAPHY_CODE.unique()

  print("Number of geographical areas: ", len(all_areas))

  all_tenures = microsynthesiser.lc4402.C_TENHUK11.unique() # assumes same as microsynthesiser.lc4404/5.C_TENHUK11
  all_occupants = microsynthesiser.lc4404.C_SIZHUK11.unique() # assumes same as microsynthesiser.lc4405.C_SIZHUK11

  # TODO make member of microsynthesiser
  categories = ["Area", "BuildType", "Tenure", "Composition", "Occupants", "Rooms", "Bedrooms", "PPerBed", "CentralHeating"]

  dwellings = pd.DataFrame(index=range(0, total_dwellings), columns=categories)

  index = 0
  for area in all_areas:
    for tenure in tenure_index:

      # 1. unconstrained usim of type and central heating 
      microsynthesiser.step1(area, tenure, index, dwellings)

      # 2. constrained usim of rooms and bedrooms
      index = microsynthesiser.step2(area, tenure, all_occupants, index, dwellings)

      # 3. "usim" of composition vs personsPerBedroom
      microsynthesiser.step3(area, tenure, dwellings)
    
    # end tenure loop

    # add communal residences
    index = microsynthesiser.add_communal(area, index, dwellings)
    
    # add unoccupied properties
    index = microsynthesiser.add_unoccupied(area, type_index, tenure_index, ch_index, index, dwellings)


  # rooms and beds for unoccupied (sampled from occupied population in same area and same BuildType)
  # TODO this is highly suboptimal, subsetting the same thing over and over again
  unocc = dwellings.loc[dwellings.Composition == 6]
  for i in unocc.index: 
    # sample from all occupied dwellings of same build type in same area
    sample = dwellings.loc[(dwellings.Area == unocc.at[i, "Area"]) 
                         & (dwellings.BuildType == unocc.at[i,"BuildType"]) 
                         & (dwellings.Composition != 6)].sample()
    assert len(sample)

    r = sample.at[sample.index[0], "Rooms"]
    b = sample.at[sample.index[0], "Bedrooms"]

    dwellings.at[i, "Rooms"] = r
    dwellings.at[i, "Bedrooms"] = b 
    dwellings.at[i, "PPerBed"] = Utils.people_per_bedroom(r, b)

  dwellings.to_csv("./synHouseholds.csv")

  print("Done. Exec time(s): ", time.time() - start_time)

  # TODO move to Utils
  print("Checking consistency...")
  # correct number of dwellings
  assert len(dwellings) == total_dwellings
  # no missing/NaN values
  assert not pd.isnull(dwellings).values.any()

  # category values are within those expected
  assert np.array_equal(sorted(dwellings.BuildType.unique()), type_index)
  #assert np.array_equal(sorted(dwellings.Tenure.unique()), tenure_index) communal residence type gets added
  #print(sorted(dwellings.Tenure.unique()))
  assert np.array_equal(sorted(dwellings.Composition.unique()), comp_index)
  assert np.array_equal(sorted(dwellings.PPerBed.unique()), ppb_index)
  assert np.array_equal(sorted(dwellings.CentralHeating.unique()), ch_index)

  # occupied/unoccupied totals correct
  assert len(dwellings[(dwellings.Composition != 6) & (dwellings.BuildType != 6)]) == total_occ_dwellings
  assert len(dwellings[dwellings.Composition == 6]) == total_households - total_occ_dwellings

  # household/communal totals correct
  assert len(dwellings[dwellings.BuildType != 6]) == total_households
  assert len(dwellings[dwellings.BuildType == 6]) == total_communal

  # BuildType
  print("BuildType: Syn, Agg")
  for i in type_index:
    if i != 6:
      print(len(dwellings[(dwellings.BuildType == i) & (dwellings.Composition != 6)]), sum(microsynthesiser.lc4402[microsynthesiser.lc4402.C_TYPACCOM == i].OBS_VALUE))
    else: 
      print(len(dwellings[(dwellings.BuildType == i) & (dwellings.Composition != 6)]), sum(microsynthesiser.communal.OBS_VALUE))

  # Tenure
  for i in tenure_index:
    assert len(dwellings[(dwellings.Tenure == i) & (dwellings.Composition != 6)]) == sum(microsynthesiser.lc4402[microsynthesiser.lc4402.C_TENHUK11 == i].OBS_VALUE)

  # central heating (ignoring unoccupied) 
  print("CentHeat: Syn, Agg")
  for i in ch_index:
    print( len(dwellings[(dwellings.CentralHeating == i) 
                       & (dwellings.Composition != 6)
                       & (dwellings.BuildType != 6)]) , sum(microsynthesiser.lc4402[microsynthesiser.lc4402.C_CENHEATHUK11 == i].OBS_VALUE))

  # composition 
  print("Comp: Syn, Agg")
  for i in comp_index:
    if i != 6:
      print(len(dwellings[(dwellings.Composition == i) & (dwellings.BuildType != 6)]),  sum(microsynthesiser.lc4408[microsynthesiser.lc4408.C_AHTHUK11 == i].OBS_VALUE))
    else:
      print(len(dwellings[(dwellings.Composition == i) & (dwellings.BuildType != 6)]),  sum(microsynthesiser.ks401[microsynthesiser.ks401.CELL == 6].OBS_VALUE))

  # Rooms (ignoring communal and unoccupied)
  assert np.array_equal(sorted(dwellings[dwellings.BuildType != 6].Rooms.unique()), microsynthesiser.lc4404["C_ROOMS"].unique())
  print("Rooms: Syn, Agg")
  for i in microsynthesiser.lc4404["C_ROOMS"].unique():
    print(len(dwellings[(dwellings.Rooms == i) 
           & (dwellings.Composition != 6)
           & (dwellings.BuildType != 6)]),  sum(microsynthesiser.lc4404[microsynthesiser.lc4404.C_ROOMS == i].OBS_VALUE))
  print("Zero rooms: ", len(dwellings[dwellings.Rooms == 0]))

  # Bedrooms (ignoring communal and unoccupied)
  assert np.array_equal(sorted(dwellings[dwellings.BuildType != 6].Bedrooms.unique()), microsynthesiser.lc4405["C_BEDROOMS"].unique())
  print("Bedrooms: Syn, Agg")
  for i in microsynthesiser.lc4405["C_BEDROOMS"].unique():
    print(len(dwellings[(dwellings.Bedrooms == i) 
           & (dwellings.Composition != 6)
           & (dwellings.BuildType != 6)]),  sum(microsynthesiser.lc4405[microsynthesiser.lc4405.C_BEDROOMS == i].OBS_VALUE))
  print("Zero bedrooms: ", len(dwellings[dwellings.Bedrooms == 0]))

  print("DONE")

if __name__ == "__main__":
  if len(sys.argv) != 3:
    print("usage:", sys.argv[0], "<region(s)> <resolution>")
    print("e.g:", sys.argv[0], "\"Newcastle upon Tyne\" OA")
    print("    ", sys.argv[0], "\"Leeds, Bradford\" MSOA")
  else:  
    region = sys.argv[1]
    resolution = sys.argv[2]
    main(region, resolution) 

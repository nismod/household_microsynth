#!/usr/bin/env python3

# run script for Household microsynthesis

import sys
import time
import numpy as np
import pandas as pd
import humanleague
import ukcensusapi.Nomisweb as Api
import household_microsynth.microsynthesis as Microsynthesiser

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
# TODO: household reference person ethnicity and economic status, no. of cars
# TODO: differentiate between purpose-built and converted flats?

def main(region, resolution):

  # start timing
  start_time = time.time()

  # specify cache directory
  microsynthesiser = Microsynthesiser.Microsynthesis(CACHE_DIR)

  # convert string to enum
  print("Microsynthesis region: ", region)
  print("Microsynthesis resolution: ", resolution)
  resolution = microsynthesiser.Area[resolution]
  #(microsynthesiser.lc4402, microsynthesiser.lc4404, microsynthesiser.lc4405, microsynthesiser.lc4408, microsynthesiser.lc1105, microsynthesiser.ks401, communal) = 
  microsynthesiser.get_census_data(region, resolution)

  # generate indices
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

  categories = ["Area", "BuildType", "Tenure", "Composition", "Occupants", "Rooms", "Bedrooms", "PPerBed", "CentralHeating"]

  dwellings = pd.DataFrame(index=range(0, total_dwellings), columns=categories)
  
  # permitted states for rooms/bedrooms
  permitted = np.ones((6, 4))
  permitted[0, 1] = 0
  permitted[0, 2] = 0
  permitted[0, 3] = 0
  permitted[1, 2] = 0
  permitted[1, 3] = 0
  permitted[2, 3] = 0

  index = 0
  for area in all_areas:
    for tenure in tenure_index:
      # 1. unconstrained usim of type and central heating 
      thdata_raw = microsynthesiser.lc4402.loc[(microsynthesiser.lc4402.GEOGRAPHY_CODE == area) 
                    & (microsynthesiser.lc4402.C_TENHUK11 == tenure)
                    & (microsynthesiser.lc4402.OBS_VALUE != 0)]
      #print(area)
      #print(thdata_raw)
      thdata = np.vstack((np.repeat(thdata_raw.C_TYPACCOM.as_matrix(), thdata_raw.OBS_VALUE.as_matrix()),
                np.repeat(thdata_raw.C_CENHEATHUK11.as_matrix(), thdata_raw.OBS_VALUE.as_matrix()))).T
      # randomise to eliminate bias w.r.t. occupants/rooms/bedrooms
      np.random.shuffle(thdata)
      #print(thdata.T)

      subindex = index
      # TODO vectorise
      for i in range(0, len(thdata)):
        dwellings.at[subindex, "BuildType"] = thdata[i][0]
        dwellings.at[subindex, "CentralHeating"] = thdata[i][1]
        subindex += 1

      # 2. constrained usim of rooms and bedrooms
      for occ in all_occupants:
        rmarginal = microsynthesiser.lc4404[(microsynthesiser.lc4404.GEOGRAPHY_CODE == area) 
                         & (microsynthesiser.lc4404.C_TENHUK11 == tenure)
                         & (microsynthesiser.lc4404.C_SIZHUK11 == occ)].OBS_VALUE.as_matrix()
        bmarginal = microsynthesiser.lc4405[(microsynthesiser.lc4405.GEOGRAPHY_CODE == area) 
                         & (microsynthesiser.lc4405.C_TENHUK11 == tenure)
                         & (microsynthesiser.lc4405.C_SIZHUK11 == occ)].OBS_VALUE.as_matrix()

        usim = humanleague.synthPopG(rmarginal, bmarginal, permitted)
        pop = usim["result"]
        assert(usim["conv"])
        #print(len(pop[0]))
        for i in range(0, len(pop[0])):
          # TODO why does moving this to above break consistency checks?
          dwellings.at[index, "Area"] = area
          dwellings.at[index, "Tenure"] = tenure
          dwellings.at[index, "Occupants"] = occ
          dwellings.at[index, "Rooms"] = pop[0][i] + 1 # since "0" means 1 room
          dwellings.at[index, "Bedrooms"] = pop[1][i] + 1
          dwellings.at[index, "PPerBed"] = people_per_bedroom(occ, pop[1][i] + 1)
          index += 1

      # 3. "usim" of composition vs personsPerBedroom
      
      # single are unambiguous
      dwellings.ix[(dwellings.Area == area)
             & (dwellings.Tenure == tenure)
             & (dwellings.Occupants == 1), "Composition"] = 1

      # randomly assign the rest (see below)
      compdata_raw = microsynthesiser.lc4408.loc[(microsynthesiser.lc4408.GEOGRAPHY_CODE == area)
                          & (microsynthesiser.lc4408.C_TENHUK11 == tenure)
                          & (microsynthesiser.lc4408.C_AHTHUK11 != 1)
                          & (microsynthesiser.lc4408.OBS_VALUE > 0)]

      compdata = np.vstack((np.repeat(compdata_raw.C_PPBROOMHEW11.as_matrix(), compdata_raw.OBS_VALUE.as_matrix()),
                 np.repeat(compdata_raw.C_AHTHUK11.as_matrix(), compdata_raw.OBS_VALUE.as_matrix()))).T

      n_not_single = len(compdata)

      # randomise to eliminate bias w.r.t. occupants/rooms/bedrooms
      np.random.shuffle(compdata)

      if n_not_single != len(dwellings[(dwellings.Area == area) 
                                    & (dwellings.Tenure == tenure) 
                                    & (dwellings.Composition != 1)]):
        print("Composition mismatch:", area, tenure, n_not_single, "vs", len(dwellings[(dwellings.Area == area) 
                                                                         & (dwellings.Tenure == tenure) 
                                                                         & (dwellings.Composition != 1)]))
      else:
        #print(compdata[:,0])
        dwellings.ix[(dwellings.Area == area)
                    & (dwellings.Tenure == tenure)
                    & (dwellings.Composition != 1), "Composition"] = compdata[:,1]
#        dwellings.ix[(dwellings.Area == area)
#                    & (dwellings.Tenure == tenure)
#                    & (dwellings.Composition != 1), "PPerBed"] = compdata[:,0]

    # communal
    area_communal = microsynthesiser.communal.loc[(microsynthesiser.communal.GEOGRAPHY_CODE == area) & (microsynthesiser.communal.OBS_VALUE > 0)]

    #print(area, len(area_communal))
    for i in range(0, len(area_communal)):
      # average occupants per establishment - integerised (special case when zero occupants)
      establishments = area_communal.at[area_communal.index[i],"OBS_VALUE"] 

      occupants = area_communal.at[area_communal.index[i],"Occupants"]
      # TODO pemit zero dwellings in prob2IntFreq to avoid this branch
      if occupants:
        occ_array = humanleague.prob2IntFreq(np.full(establishments, 1.0 / establishments), occupants)["freq"]
      else:
        occ_array = np.zeros(establishments)
      #print(occ_array)

      # row indices are the original values from the entire table
      for j in range(0, establishments):
        dwellings.at[index, "Area"] = area
        dwellings.at[index, "BuildType"] = 6
        # TODO check j is correct index? (R code uses i)
        dwellings.at[index, "Tenure"] = 100 + area_communal.at[area_communal.index[i], "CELL"]
        dwellings.at[index, "Occupants"] = occ_array[j]
        # TODO if zero occupants, how to set rooms/beds? mean value of establishment type in region? 
        dwellings.at[index, "Rooms"] = occ_array[j]
        dwellings.at[index, "Bedrooms"] = occ_array[j]
        dwellings.at[index, "Composition"] = 5
        dwellings.at[index, "PPerBed"] = 2
        dwellings.at[index, "CentralHeating"] = 2 # assume all communal are centrally heated
        index += 1
    
    # unoccupied, should be one entry per area
    # microsynthesise the occupied houses by BuildType, Tenure, CentralHeating and sample the unoccupied from this dwellings
    unocc = microsynthesiser.ks401.loc[(microsynthesiser.ks401.GEOGRAPHY_CODE == area) & (microsynthesiser.ks401.CELL == 6)]
    assert len(unocc == 1)
    n_unocc = unocc.at[unocc.index[0], "OBS_VALUE"]

    if n_unocc:
      # type marginal
      type_tenure_ch = microsynthesiser.lc4402.loc[microsynthesiser.lc4402.GEOGRAPHY_CODE == area]
      type_marginal = type_tenure_ch.groupby("C_TYPACCOM").agg({"OBS_VALUE":np.sum})["OBS_VALUE"].as_matrix()
      # tenure marginal
      tenure_marginal = type_tenure_ch.groupby("C_TENHUK11").agg({"OBS_VALUE":np.sum})["OBS_VALUE"].as_matrix()
      # central heating marginal
      centheat_marginal = type_tenure_ch.groupby("C_CENHEATHUK11").agg({"OBS_VALUE":np.sum})["OBS_VALUE"].as_matrix()

      # TODO return np.array...
      uusim = humanleague.synthPop([type_marginal, tenure_marginal, centheat_marginal])
      assert(uusim["conv"])
      # randomly sample n_unocc values
      occ_pop = pd.DataFrame(np.array(uusim["result"]).T, columns=["BuildType","Tenure","CentralHeating"])
      # use without-replacement sampling if possible
      unocc_pop = occ_pop.sample(n = n_unocc, replace = len(occ_pop) < n_unocc)
      # we now potentially have duplicate index values which can cause problems indexing
#      print(unocc_pop.head(10))
      unocc_pop = unocc_pop.reset_index(drop=True)
#      print(unocc_pop.head(10))

      for j in range(0, n_unocc):
        dwellings.at[index, "Area"] = area
        dwellings.at[index, "BuildType"] = type_index[unocc_pop.at[j, "BuildType"]]
        dwellings.at[index, "Tenure"] = tenure_index[unocc_pop.at[j, "Tenure"]]
        dwellings.at[index, "Occupants"] = 0
#        # Rooms/beds are done at the end (so we can sample dwellings)
        dwellings.at[index, "Rooms"] = 0
        dwellings.at[index, "Bedrooms"] = 0
        dwellings.at[index, "Composition"] = 6
        dwellings.at[index, "PPerBed"] = 1
        dwellings.at[index, "CentralHeating"] = ch_index[unocc_pop.at[j, "CentralHeating"]]
        index += 1


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
    dwellings.at[i, "PPerBed"] = people_per_bedroom(r, b)

  dwellings.to_csv("./synHouseholds.csv")

  print("Done. Exec time(s): ", time.time() - start_time)

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



# TODO make private static nonmember...
def people_per_bedroom(people, bedrooms):
  ppbed = people / bedrooms
  if ppbed <= 0.5:
    return 1 # (0,0.5]
  if ppbed <= 1:
    return 2 # (0.5, 1]
  if ppbed <= 1.5:
    return 3 # (1, 1.5]
  return 4 # >1.5

if __name__ == "__main__":
  if len(sys.argv) != 3:
    print("usage:", sys.argv[0], "<region(s)> <resolution>")
    print("e.g:", sys.argv[0], "\"Newcastle upon Tyne\" OA")
    print("    ", sys.argv[0], "\"Leeds, Bradford\" MSOA")
  else:  
    region = sys.argv[1]
    resolution = sys.argv[2]
    main(region, resolution) 



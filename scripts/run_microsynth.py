#!/usr/bin/env python3

# run script for Household microsynthesis

import time
import numpy as np
import pandas as pd
import humanleague
import ukcensusapi.Nomisweb as Api
import household_microsynth.Microsynthesis as Microsynthesiser

assert humanleague.version() == 1

# Set country or local authority/ies here
REGION = "City of London"
# Set resolution LA/MSOA/LSOA/OA
RESOLUTION = Api.Nomisweb.OA

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

def main():

  # start timing
  start_time = time.time()

  # specify cache directory
  microsynthesiser = Microsynthesiser.Microsynthesis("/tmp/UKCensusAPI")

  (LC4402, LC4404, LC4405, LC4408, LC1105, KS401, COMMUNAL) = microsynthesiser.get_census_data(REGION, RESOLUTION)

  # generate indices
  type_index = LC4402.C_TYPACCOM.unique()
  type_index = np.append(type_index, 6) # this value denotes communal
  tenure_index = LC4402.C_TENHUK11.unique()
  ch_index = LC4402.C_CENHEATHUK11.unique()
  print(ch_index)
  ppb_index = LC4408.C_PPBROOMHEW11.unique()
  comp_index = LC4408.C_AHTHUK11.unique()
  comp_index = np.append(comp_index, 6) # this value denotes unoccupied

  # Do some basic checks on totals
  total_occ_dwellings = sum(LC4402.OBS_VALUE)
  print(total_occ_dwellings)
  assert sum(LC4404.OBS_VALUE) == total_occ_dwellings
  assert sum(LC4405.OBS_VALUE) == total_occ_dwellings
  assert sum(LC4408.OBS_VALUE) == total_occ_dwellings
  assert sum(KS401[KS401.CELL == 5].OBS_VALUE) == total_occ_dwellings

  total_dwellings = sum(LC1105.OBS_VALUE)
  total_households = sum(KS401.OBS_VALUE)
  total_communal = sum(COMMUNAL.OBS_VALUE)
  total_dwellings = total_households + total_communal

  occ_pop_lbound = sum(LC4404.C_SIZHUK11 * LC4404.OBS_VALUE)
  household_dwellings = sum(LC1105[LC1105.C_RESIDENCE_TYPE == 1].OBS_VALUE)
  communal_dwellings = sum(LC1105[LC1105.C_RESIDENCE_TYPE == 2].OBS_VALUE)

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

  all_areas = LC4402.GEOGRAPHY_CODE.unique()
  all_tenures = LC4402.C_TENHUK11.unique() # assumes same as LC4404/5.C_TENHUK11
  all_occupants = LC4404.C_SIZHUK11.unique() # assumes same as LC4405.C_SIZHUK11
  all_p_per_beds = LC4408.C_PPBROOMHEW11.unique() 

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
    for tenure in all_tenures:
      # 1. unconstrained usim of type and central heating 
      thdata_raw = LC4402.loc[(LC4402.GEOGRAPHY_CODE == area) 
                    & (LC4402.C_TENHUK11 == tenure)
                    & (LC4402.OBS_VALUE != 0)]
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
        rmarginal = LC4404[(LC4404.GEOGRAPHY_CODE == area) 
                         & (LC4404.C_TENHUK11 == tenure)
                         & (LC4404.C_SIZHUK11 == occ)].OBS_VALUE.as_matrix()
        bmarginal = LC4405[(LC4405.GEOGRAPHY_CODE == area) 
                         & (LC4405.C_TENHUK11 == tenure)
                         & (LC4405.C_SIZHUK11 == occ)].OBS_VALUE.as_matrix()

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
      compdata_raw = LC4408.loc[(LC4408.GEOGRAPHY_CODE == area)
                          & (LC4408.C_TENHUK11 == tenure)
                          & (LC4408.C_AHTHUK11 != 1)
                          & (LC4408.OBS_VALUE > 0)]

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
    area_communal = COMMUNAL.loc[(COMMUNAL.GEOGRAPHY_CODE == area) & (COMMUNAL.OBS_VALUE > 0)]

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
        dwellings.at[index, "Rooms"] = occ_array[j]
        dwellings.at[index, "Bedrooms"] = occ_array[j]
        dwellings.at[index, "Composition"] = 5
        dwellings.at[index, "PPerBed"] = 2
        dwellings.at[index, "CentralHeating"] = 2 # assume all communal are centrally heated
        index += 1
    
    # unoccupied, should be one entry per area
    # microsynthesise the occupied houses by BuildType, Tenure, CentralHeating and sample the unoccupied from this dwellings
    unocc = KS401.loc[(KS401.GEOGRAPHY_CODE == area) & (KS401.CELL == 6)]
    assert len(unocc == 1)
    n_unocc = unocc.at[unocc.index[0], "OBS_VALUE"]

    if n_unocc:
      # type marginal
      type_tenure_ch = LC4402.loc[LC4402.GEOGRAPHY_CODE == area]
      type_marginal = type_tenure_ch.groupby("C_TYPACCOM").agg({"OBS_VALUE":np.sum})["OBS_VALUE"].as_matrix()
      # tenure marginal
      tenure_marginal = type_tenure_ch.groupby("C_TENHUK11").agg({"OBS_VALUE":np.sum})["OBS_VALUE"].as_matrix()
      # central heating marginal
      centheat_marginal = type_tenure_ch.groupby("C_CENHEATHUK11").agg({"OBS_VALUE":np.sum})["OBS_VALUE"].as_matrix()

      # TODO return np.array...so can shuffle directly
      uusim = humanleague.synthPop([type_marginal, tenure_marginal, centheat_marginal])
      assert(uusim["conv"])
      # randomise and take the first n_unocc values
      occ_pop = np.array(uusim["result"])
      np.random.shuffle(occ_pop) 

      for j in range(0, n_unocc):
        dwellings.at[index, "Area"] = area
        # TODO check j is correct index
        dwellings.at[index, "BuildType"] = type_index[uusim["result"][0][j]]
        dwellings.at[index, "Tenure"] = tenure_index[uusim["result"][1][j]]
        dwellings.at[index, "Occupants"] = 0
        # Rooms/beds are done at the end (so we can sample dwellings)
        dwellings.at[index, "Rooms"] = 9
        dwellings.at[index, "Bedrooms"] = 9
        dwellings.at[index, "Composition"] = 6
        dwellings.at[index, "PPerBed"] = 1
        dwellings.at[index, "CentralHeating"] = ch_index[uusim["result"][2][j]]
        index += 1

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
      print(len(dwellings[(dwellings.BuildType == i) & (dwellings.Composition != 6)]), sum(LC4402[LC4402.C_TYPACCOM == i].OBS_VALUE))
    else: 
      print(len(dwellings[(dwellings.BuildType == i) & (dwellings.Composition != 6)]), sum(COMMUNAL.OBS_VALUE))

  # Tenure
  for i in tenure_index:
    assert len(dwellings[(dwellings.Tenure == i) & (dwellings.Composition != 6)]) == sum(LC4402[LC4402.C_TENHUK11 == i].OBS_VALUE)

  # central heating (ignoring unoccupied) 
  print("CentHeat: Syn, Agg")
  for i in ch_index:
    print( len(dwellings[(dwellings.CentralHeating == i) 
                       & (dwellings.Composition != 6)
                       & (dwellings.BuildType != 6)]) , sum(LC4402[LC4402.C_CENHEATHUK11 == i].OBS_VALUE))

  # composition 
  print("Comp: Syn, Agg")
  for i in comp_index:
    if i != 6:
      print(len(dwellings[(dwellings.Composition == i) & (dwellings.BuildType != 6)]),  sum(LC4408[LC4408.C_AHTHUK11 == i].OBS_VALUE))
    else:
      print(len(dwellings[(dwellings.Composition == i) & (dwellings.BuildType != 6)]),  sum(KS401[KS401.CELL == 6].OBS_VALUE))

  print("DONE")


# TODO make private static nonmember...
def people_per_bedroom(people, bedrooms):
  ppbed = people / bedrooms
  if ppbed <= 0.5:
    return 1 # (0,0.5]
  elif ppbed <= 1:
    return 2 # (0.5, 1]
  elif ppbed <= 1.5:
    return 3 # (1, 1.5]
  else: 
    return 4 # >1.5

if __name__ == "__main__":
  main()


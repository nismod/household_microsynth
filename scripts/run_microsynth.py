#!/usr/bin/env python3

# run script for Household microsynthesis

import time
import numpy as np
import pandas as pd
import humanleague
import ukcensusapi.Nomisweb as Api
import household_microsynth.Microsynthesis as Microsynthesiser

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

  # Do some basic checks on totals
  total_occ_dwellings = sum(LC4402.OBS_VALUE)
  print(total_occ_dwellings)
  assert sum(LC4404.OBS_VALUE) == total_occ_dwellings
  assert sum(LC4405.OBS_VALUE) == total_occ_dwellings
  assert sum(LC4408.OBS_VALUE) == total_occ_dwellings
  assert sum(KS401[KS401.CELL == 5].OBS_VALUE) == total_occ_dwellings

  total_population = sum(LC1105.OBS_VALUE)
  total_households = sum(KS401.OBS_VALUE)
  total_communal = sum(COMMUNAL.OBS_VALUE)
  total_dwellings = total_households + total_communal

  occ_pop_lbound = sum(LC4404.C_SIZHUK11 * LC4404.OBS_VALUE)
  household_population = sum(LC1105[LC1105.C_RESIDENCE_TYPE == 1].OBS_VALUE)
  communal_population = sum(LC1105[LC1105.C_RESIDENCE_TYPE == 2].OBS_VALUE)

  print("Households: ", total_households)
  print("Occupied households: ", total_occ_dwellings)
  print("Unoccupied dwellings: ", total_households - total_occ_dwellings)
  print("Communal residences: ", total_communal)
  print("Dwellings: ", total_dwellings)

  print("Total population: ", total_population)
  print("Population in occupied households: ", household_population)
  print("Population in communal residences: ", communal_population)
  print("Population lower bound from occupied households: ", occ_pop_lbound)
  print("Occupied household population underestimate: ", household_population - occ_pop_lbound)

  # TODO move this code into the Microsynthesise class...

  all_areas = LC4402.GEOGRAPHY_CODE.unique()
  all_tenures = LC4402.C_TENHUK11.unique() # assumes same as LC4404/5.C_TENHUK11
  all_occupants = LC4404.C_SIZHUK11.unique() # assumes same as LC4405.C_SIZHUK11
  all_p_per_beds = LC4408.C_PPBROOMHEW11.unique() 
  
#  print(all_areas)
#  print(all_tenures)
#  print(all_occupants)
#  print(all_p_per_beds)
  
  categories = ["Area","BuildType","Tenure", "Composition", "Occupants", "Rooms", "Bedrooms", "PPerBed", "CentralHeating"]

  population = pd.DataFrame(index=range(0, total_dwellings + total_communal), columns=categories)
  
  # permitted states for rooms/bedrooms
  permitted = np.ones((6, 4))
  permitted[0,1] = 0
  permitted[0,2] = 0
  permitted[0,3] = 0
  permitted[1,2] = 0
  permitted[1,3] = 0
  permitted[2, 3] = 0

  #print(permitted)

  index = 0
  for area in all_areas:
    for tenure in all_tenures:
      # 1. unconstrained usim of type and central heating 
      thdata = LC4402[(LC4402.GEOGRAPHY_CODE == area) 
                    & (LC4402.C_TENHUK11 == tenure)
                    & (LC4402.OBS_VALUE != 0)]
      thdata = np.vstack((np.repeat(thdata.C_TYPACCOM.as_matrix(), thdata.OBS_VALUE.as_matrix()),
                np.repeat(thdata.C_CENHEATHUK11.as_matrix(), thdata.OBS_VALUE.as_matrix()))).T
      # randomise to eliminate bias w.r.t. occupants/rooms/bedrooms
      np.random.shuffle(thdata)

      subindex = index
      # TODO vectorise
      for i in range(0, len(thdata)):
        population.at[subindex, "BuildType"] = thdata[0][0] 
        population.at[subindex, "CentralHeating"] = thdata[0][1] - 1 
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
          population.at[index, "Area"] = area # TODO move to step 1?
          population.at[index, "Tenure"] = tenure # TODO move to step 1?
          population.at[index, "Occupants"] = occ # TODO move to step 1?
          population.at[index, "Rooms"] = pop[0][i] + 1 # since "0" means 1 room
          population.at[index, "Bedrooms"] = pop[1][i] + 1 
          population.at[index, "PPerBed"] = people_per_bedroom(occ, pop[1][i] + 1) 
          index += 1

      # 3. "usim" of composition vs personsPerBedroom
      
      # single are unambiguous
      population.ix[(population.Area == area)
             & (population.Tenure == tenure)
             & (population.Occupants == 1), "Composition"] = 1

      # randomly assign the rest (see below)
      compdata = LC4408.loc[(LC4408.GEOGRAPHY_CODE == area)
                          & (LC4408.C_TENHUK11 == tenure)
                          & (LC4408.C_AHTHUK11 != 1)
                          & (LC4408.OBS_VALUE > 0)]

      compdata = np.vstack((np.repeat(compdata.C_PPBROOMHEW11.as_matrix(), compdata.OBS_VALUE.as_matrix()),
                 np.repeat(compdata.C_AHTHUK11.as_matrix(), compdata.OBS_VALUE.as_matrix()))).T

      n_not_single = len(compdata)

      # randomise to eliminate bias w.r.t. occupants/rooms/bedrooms
      np.random.shuffle(compdata)

      if n_not_single != len(population[(population.Area == area) 
                                    & (population.Tenure == tenure) 
                                    & (population.Composition != 1)]):
        print("Composition mismatch:", area, tenure, n_not_single, "vs", len(population[(population.Area == area) 
                                                                         & (population.Tenure == tenure) 
                                                                         & (population.Composition != 1)]))
      else:
        population.ix[(population.Area == area)
                    & (population.Tenure == tenure)
                    & (population.Composition != 1), "Composition"] = compdata[:,0]
#        population.ix[(population.Area == area)
#                    & (population.Tenure == tenure)
#                    & (population.Composition != 1), "PPerBed"] = compdata[:,1]

    # communal
#    oaCommunal = COMMUNAL.loc[(COMMUNAL.GEOGRAPHY_CODE == area) & (COMMUNAL.OBS_VALUE > 0) ]
#    
#    print(area, len(oaCommunal))
#    for i in range(0, len(oaCommunal)):
#      # average occupants per establishment - integerised (special case when zero occupants)
##      occs = rep(0L, oaCommunal[i,]$Occupants)
## OBS_VALUE = no. of establishments
##      if ( oaCommunal[i,]$Occupants > 0) {
##        occs = humanleague::prob2IntFreq(rep(1/oaCommunal[i,]$Count, oaCommunal[i,]$Count), oaCommunal[i,]$Occupants)$freq
##      }

#      print(i, oaCommunal)
#      for j in range(0, oaCommunal.at[i,"OBS_VALUE"]):
#        population.at[index, "Area"] = area
#        population.at[index, "BuildType"] = 6
#        population.at[index, "Tenure"] = 100 + oaCommunal[i,"TypeCode"]
#        population.at[index, "Occupants"] = 99
#        population.at[index, "Rooms"] = 99
#        population.at[index, "Bedrooms"] = 99
#        population.at[index, "Composition"] = 5
#        population.at[index, "PPerBed"] = 2
#        population.at[index, "CentralHeating"] = 1
#        index += 1
    
    # TODO unoccupied

  population.to_csv("./synHouseholds.csv")

  print("Done. Exec time(s): ", time.time() - start_time)

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


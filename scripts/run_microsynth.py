#!/usr/bin/env python3

"""
run script for Household microsynthesis
"""

import time
import argparse
import humanleague
#import ukcensusapi.Nomisweb as Api
import household_microsynth.household as hh_msynth
import household_microsynth.ref_person as hrp_msynth
import household_microsynth.utils as Utils

assert humanleague.version() > 1
CACHE_DIR = "./cache"
OUTPUT_DIR = "./data"

# The microsynthesis makes use of the following tables:
# LC4402EW - Accommodation type by type of central heating in household by tenure
# LC4404EW - Tenure by household size by number of rooms
# LC4405EW - Tenure by household size by number of bedrooms
# LC4408EW - Tenure by number of persons per bedroom in household by household type
# LC1105EW - Residence type by sex by age
# KS401EW - Dwellings, household spaces and accommodation type
# QS420EW - Communal establishment management and type - Communal establishments
# QS421EW - Communal establishment management and type - People
# LC4202EW - Tenure by car or van availability by ethnic group of Household Reference Person (HRP)
# LC4601EW - Tenure by economic activity by age - Household Reference Persons
# TODO: differentiate between purpose-built and converted flats?

def main(region, resolution):
  """ Entry point """
  #do_hh(region, resolution)
  do_hrp(region, resolution)


def do_hh(region, resolution):
  """ Do households """

  # # start timing
  start_time = time.time()

  print("Microsynthesis target: households")
  print("Microsynthesis region:", region)
  print("Microsynthesis resolution:", resolution)
  # init microsynthesis
  try:
    msynth = hh_msynth.Household(region, resolution, CACHE_DIR)
  except Exception as error:
    print(error)
    return

  # Do some basic checks on totals
  total_occ_dwellings = sum(msynth.lc4402.OBS_VALUE)
  assert sum(msynth.lc4404.OBS_VALUE) == total_occ_dwellings
  assert sum(msynth.lc4405.OBS_VALUE) == total_occ_dwellings
  assert sum(msynth.lc4408.OBS_VALUE) == total_occ_dwellings
  assert sum(msynth.ks401[msynth.ks401.CELL == 5].OBS_VALUE) == total_occ_dwellings

  total_population = sum(msynth.lc1105.OBS_VALUE)
  total_households = sum(msynth.ks401.OBS_VALUE)
  total_communal = sum(msynth.communal.OBS_VALUE)
  total_dwellings = total_households + total_communal

  occ_pop_lbound = sum(msynth.lc4404.C_SIZHUK11 * msynth.lc4404.OBS_VALUE)
  household_pop = sum(msynth.lc1105[msynth.lc1105.C_RESIDENCE_TYPE == 1].OBS_VALUE)
  communal_pop = sum(msynth.lc1105[msynth.lc1105.C_RESIDENCE_TYPE == 2].OBS_VALUE)

  print("Households: ", total_households)
  print("Occupied households: ", total_occ_dwellings)
  print("Unoccupied dwellings: ", total_households - total_occ_dwellings)
  print("Communal residences: ", total_communal)

  print("Total dwellings: ", total_dwellings)
  print("Total population: ", total_population)
  print("Population in occupied households: ", household_pop)
  print("Population in communal residences: ", communal_pop)
  print("Population lower bound from occupied households: ", occ_pop_lbound)
  print("Occupied household dwellings underestimate: ", household_pop - occ_pop_lbound)

  print("Number of geographical areas: ", len(msynth.lc4402.GEOGRAPHY_CODE.unique()))

  # generate the population
  try:
    msynth.run()
  except Exception as error:
    print(error)
    return

  print("Done. Exec time(s): ", time.time() - start_time)

  print("Checking consistency")
  success = Utils.check_hh(msynth, total_occ_dwellings, total_households, total_communal, occ_pop_lbound, communal_pop)
  if success:
    print("ok")
  else:
    print("failed")
  output = OUTPUT_DIR + "/hh_" + region + "_" + resolution + ".csv"
  print("Writing synthetic population to", output)
  msynth.dwellings.to_csv(output)
  print("DONE")

def do_hrp(region, resolution):
  """ Do household ref persons """
  
  # # start timing
  start_time = time.time()

  print("Microsynthesis target: household ref persons")
  print("Microsynthesis region:", region)
  print("Microsynthesis resolution:", resolution)
  # init microsynthesis
  #try:
  msynth = hrp_msynth.ReferencePerson(region, resolution, CACHE_DIR)
  #except Exception as error:
  #  print(error)
  #  return

  # Do some basic checks on totals 
  # TODO this should probably be in ref_person.py
  total_hrps = sum(msynth.lc4201.OBS_VALUE) 
  assert sum(msynth.qs111.OBS_VALUE) == total_hrps
  assert sum(msynth.lc1102.OBS_VALUE) == total_hrps

  if sum(msynth.lc4605.OBS_VALUE) != total_hrps:
    lc4605_hrps = sum(msynth.lc4605.OBS_VALUE)
    print("Count mismatch in table LC4605 ("+str(lc4605_hrps)+ ") will be adjusted. (Likely missing HRPs aged under 16)" )

  print("Households: ", total_hrps)

  print("Number of geographical areas: ", len(msynth.lc4605.GEOGRAPHY_CODE.unique()))

  # generate the population
  #try:
  msynth.run()
  #except Exception as error:
  #  print(error)
  #  return

  print("Done. Exec time(s): ", time.time() - start_time)

  print("Checking consistency")
  success = Utils.check_hrp(msynth, total_hrps)
  if success:
    print("ok")
  else:
    print("failed")
  output = OUTPUT_DIR + "/hrp_" + region + "_" + resolution + ".csv"
  print("Writing synthetic population to", output)
  msynth.hrps.to_csv(output)
  print("DONE")


if __name__ == "__main__":

  parser = argparse.ArgumentParser(description="household microsynthesis")
  parser.add_argument("region", type=str, help="the ONS code of the local authority district (LAD) to be covered by the microsynthesis, e.g. E09000001")
  parser.add_argument("resolution", type=str, help="the geographical resolution of the microsynthesis (e.g. OA11, LSOA11, MSOA11)")
  # TODO add flags for hh and/or hrp 

  args = parser.parse_args()

  main(args.region, args.resolution)

import numpy as np
from pandas import MultiIndex
from random import randint

import humanleague as hl
import ukcensusapi.Nomisweb as Api

import household_microsynth.utils as Utils

api = Api.Nomisweb("./cache")

resolution = api.GeoCodeLookup["OA11"]

lad_codes = api.get_lad_codes("Newcastle upon Tyne")

area_codes = api.get_geo_codes(lad_codes, resolution)

common_params = {"MEASURES": "20100",
                 "date": "latest",
                 "geography": area_codes}

# LC4404EW - Tenure by household size by number of rooms
table = "NM_889_1"
query_params = common_params.copy()
query_params["C_ROOMS"] = "1...6"
query_params["C_TENHUK11"] = "2,3,5,6"
query_params["C_SIZHUK11"] = "1...4"
query_params["select"] = "GEOGRAPHY_CODE,C_ROOMS,C_TENHUK11,C_SIZHUK11,OBS_VALUE"
lc4404 = api.get_data("LC4404EW", table, query_params)

# LC4405EW - Tenure by household size by number of bedrooms
table = "NM_890_1"
query_params = common_params.copy()
query_params["C_TENHUK11"] = "2,3,5,6"
query_params["C_BEDROOMS"] = "1...4"
query_params["C_SIZHUK11"] = "1...4"
query_params["select"] = "GEOGRAPHY_CODE,C_SIZHUK11,C_TENHUK11,C_BEDROOMS,OBS_VALUE"
lc4405 = api.get_data("LC4405EW", table, query_params)

# LC4402EW - Accommodation type by type of central heating in household by tenure
table = "NM_887_1"
query_params = common_params.copy()
query_params["C_TENHUK11"] = "2,3,5,6"
query_params["C_CENHEATHUK11"] = "1,2"
query_params["C_TYPACCOM"] = "2...5"
query_params["select"] = "GEOGRAPHY_CODE,C_TENHUK11,C_CENHEATHUK11,C_TYPACCOM,OBS_VALUE"
lc4402 = api.get_data("LC4402EW", table, query_params)

# LC4202EW - Tenure by car or van availability by ethnic group of Household Reference Person (HRP)
table = "NM_880_1"
query_params = common_params.copy()
query_params["C_CARSNO"] = "1...3"
query_params["C_TENHUK11"] = "2,3,5,6"
query_params["C_ETHHUK11"] = "2...8"
query_params["select"] = "GEOGRAPHY_CODE,C_ETHHUK11,C_CARSNO,C_TENHUK11,OBS_VALUE"
lc4202 = api.get_data("LC4202EW", table, query_params)

# LC4601EW - Tenure by economic activity by age - Household Reference Persons
table = "NM_899_1"
query_params = common_params.copy()
query_params["C_TENHUK11"] = "2,3,5,6"
query_params["C_ECOPUK11"] = "4,5,7,8,9,11,12,14...18"
query_params["C_AGE"] = "0"
query_params["select"] = "GEOGRAPHY_CODE,C_TENHUK11,C_ECOPUK11,OBS_VALUE"
lc4601 = api.get_data("LC4601EW", table, query_params)

#                                           DIM
area_map = lc4404.GEOGRAPHY_CODE.unique() 
rooms_map = [1, 2, 3, 4, 5, 6]            #  1
tenure_map = [2, 3, 5, 6]                 #  0
occupants_map = [1, 2, 3, 4]              #  2
bedrooms_map = [1, 2, 3, 4]               #  3

#                           
ch_map = [1, 2]                           #  1 
accom_map = [2, 3, 4, 5]                  #  2
eth_map = [2, 3, 4, 5, 6, 7, 8]           #  3
cars_map = [1, 2, 3]                       #  4
econ_map = [4,5,7,8,9,11,12,14,15,16,17,18] # 5

# construct seed disallowing states where B>R]
#            T  R  S  B
s = np.ones([4, 6, 4, 4])
# set  = 0
for r in range(0,6):
  for b in range(r+1,4):
    s[:,r,:,b] = 0

#print (len(area_map))
for area in area_map[10:]:
  tenure_rooms_occ = lc4404.loc[lc4404.GEOGRAPHY_CODE == area].copy()
  # unmap indices
# TODO might be quicker to unmap the entire table upfront
  Utils.unmap(tenure_rooms_occ.C_TENHUK11, tenure_map)
  Utils.unmap(tenure_rooms_occ.C_ROOMS, rooms_map)
  Utils.unmap(tenure_rooms_occ.C_SIZHUK11, occupants_map)

  m4404 = Utils.unlistify(tenure_rooms_occ, 
                          ["C_TENHUK11","C_ROOMS","C_SIZHUK11"], 
                          [len(tenure_map),len(rooms_map),len(occupants_map)], 
                          "OBS_VALUE")

  tenure_beds_occ = lc4405.loc[lc4405.GEOGRAPHY_CODE == area].copy()

  # unmap indices
  Utils.unmap(tenure_beds_occ.C_BEDROOMS, rooms_map)
  Utils.unmap(tenure_beds_occ.C_TENHUK11, tenure_map)
  Utils.unmap(tenure_beds_occ.C_SIZHUK11, occupants_map)

  m4405 = Utils.unlistify(tenure_beds_occ,
                          ["C_TENHUK11","C_BEDROOMS","C_SIZHUK11"],
                          [len(tenure_map),len(bedrooms_map),len(occupants_map)],
                          "OBS_VALUE")

  # p = hl.qis([np.array([0,1,2]), np.array([0,3,2]), np.array([0,4,5])], [m4404, m4405, m4402])
  # if isinstance(p, str):
  #   print(area + " QIS: " + p)
  # else:
  #   print(area + " QIS: " + str(p["conv"]))

  # p = hl.ipf(s, [np.array([0,1,2]), np.array([0,3,2]), np.array([0,4,5])], [m4404.astype(float), m4405.astype(float), m4402.astype(float)])
  # print(area + " IPF: " + str(p["conv"]))

  # TODO relax IPF tolerance and maxiters when used within QISI?
  p0 = hl.qisi(s, [np.array([0,1,2]), np.array([0,3,2])], [m4404, m4405])
  if isinstance(p0, str):
    print(area + " QIS-I: " + p0)
  else:
    print(area + " QIS-I: " + str(p0["conv"]))

  tenure_ch_accom = lc4402.loc[lc4402.GEOGRAPHY_CODE == area].copy()
  Utils.unmap(tenure_ch_accom.C_CENHEATHUK11, ch_map)
  Utils.unmap(tenure_ch_accom.C_TENHUK11, tenure_map)
  Utils.unmap(tenure_ch_accom.C_TYPACCOM, accom_map)

  m4402 = Utils.unlistify(tenure_ch_accom,
                          ["C_TENHUK11","C_CENHEATHUK11","C_TYPACCOM"],
                          [len(tenure_map),len(bedrooms_map),len(occupants_map)],
                          "OBS_VALUE")

  tenure_eth_car = lc4202.loc[lc4202.GEOGRAPHY_CODE == area].copy()
  Utils.unmap(tenure_eth_car.C_ETHHUK11, eth_map)
  Utils.unmap(tenure_eth_car.C_CARSNO, cars_map)
  Utils.unmap(tenure_eth_car.C_TENHUK11, tenure_map)

  m4202 = Utils.unlistify(tenure_eth_car,
                          ["C_TENHUK11","C_ETHHUK11","C_CARSNO"],
                          [len(tenure_map),len(eth_map),len(cars_map)],
                          "OBS_VALUE")

  econ = lc4601.loc[lc4601.GEOGRAPHY_CODE == area].copy()
  Utils.unmap(econ.C_ECOPUK11, econ_map)
  Utils.unmap(econ.C_TENHUK11, tenure_map)

  # print(tenure_eth_car.OBS_VALUE.sum())
  # print(econ.OBS_VALUE.sum())
  econ = Utils.adjust(econ, tenure_eth_car)

  m4601 = Utils.unlistify(econ,
                          ["C_TENHUK11","C_ECOPUK11"],
                          [len(tenure_map),len(econ_map)],
                          "OBS_VALUE")
  # counts often slightly lower


  # no seed constraint so just use QIS
  p1 = hl.qis([np.array([0, 1, 2, 3]), np.array([0, 4, 5]), np.array([0, 6, 7]), np.array([0, 8])], [p0["result"], m4402, m4202, m4601])
  if isinstance(p1, str):
    print(area + " QIS: " + p1)
  else:
    print(area + " QIS: " + str(p1["conv"]))

  # # now combine the two populations (tied by tenure)
  # p = hl.qis([np.array([0, 1, 2, 3]), np.array([0, 4, 5, 6, 7])], [p0["result"], p1["result"]])
  # if isinstance(p, str):
  #   print(area + " QIS (comb): " + p)
  # else:
  #   print(area + " QIS (comb): " + str(p["conv"]))

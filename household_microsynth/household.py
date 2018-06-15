""" Household microsynthesis """

import numpy as np
import pandas as pd

import ukcensusapi.Nomisweb as Api_ew
import ukcensusapi.NRScotland as Api_sc
import humanleague
import household_microsynth.utils as Utils

class Household:
  """ Household microsynthesis """

  # Placeholders for unknown or non-applicable category values
  UNKNOWN = -1
  NOTAPPLICABLE = -2

  # initialise, supplying geographical area and resolution , plus (optionally) a location to cache downloads
  def __init__(self, region, resolution, cache_dir="./cache"):
    self.api_ew = Api_ew.Nomisweb(cache_dir)
    self.api_sc = Api_sc.NRScotland(cache_dir)

    self.region = region
    # convert input string to enum
    self.resolution = resolution

    # (down)load the census tables
    self.__get_census_data()

    # initialise table and index
    categories = ["Area", "LC4402_C_TYPACCOM", "QS420EW_CELL", "LC4402_C_TENHUK11", "LC4408_C_AHTHUK11", "CommunalSize",
                  "LC4404EW_C_SIZHUK11", "LC4404EW_C_ROOMS", "LC4405EW_C_BEDROOMS", "LC4408EW_C_PPBROOMHEW11",
                  "LC4402_C_CENHEATHUK11", "LC4605EW_C_NSSEC", "LC4202EW_C_ETHHUK11", "LC4202EW_C_CARSNO"]
    self.total_dwellings = sum(self.ks401.OBS_VALUE) + sum(self.communal.OBS_VALUE)
#    self.dwellings = pd.DataFrame(index=range(0, self.total_dwellings), columns=categories)
    self.dwellings = pd.DataFrame(columns=categories)
    self.index = 0

    # generate indices
    self.type_index = self.lc4402.C_TYPACCOM.unique()
    self.tenure_index = self.lc4402.C_TENHUK11.unique()
    self.ch_index = self.lc4402.C_CENHEATHUK11.unique()
    #self.ppb_index = self.lc4408.C_PPBROOMHEW11.unique()
    self.comp_index = self.lc4408.C_AHTHUK11.unique()

  def run(self):
    """ run the microsynthesis """

    area_map = self.lc4404.GEOGRAPHY_CODE.unique()

    # construct seed disallowing states where B>R]
    #                           T  R  O  B  X  (X=household type)
    constraints = np.ones([4, 6, 4, 4, 5])
    # forbid bedrooms>rooms
    for r in range(0, 6): # use rooms/beds map sizes
      for b in range(r+1, 4):
        constraints[:, r, :, b, :] = 0
    # constrain single person household to occupants=1
    constraints[:, :, 0, :, 1] = 0
    constraints[:, :, 0, :, 2] = 0
    constraints[:, :, 0, :, 3] = 0
    constraints[:, :, 0, :, 4] = 0
    constraints[:, :, 1, :, 0] = 0
    constraints[:, :, 2, :, 0] = 0
    constraints[:, :, 3, :, 0] = 0

    for area in area_map:
      print('.', end='', flush=True)

      # 1. households
      self.__add_households(area, constraints)

      # add communal residences
      self.__add_communal(area)

      # # add unoccupied properties
      self.__add_unoccupied(area)

      # end area loop

    # temp fix - TODO remove this column?
    self.dwellings.LC4408EW_C_PPBROOMHEW11 = np.repeat(self.UNKNOWN, len(self.dwellings.LC4408EW_C_PPBROOMHEW11))

  def __add_households(self, area, constraints):

    # TODO remove - duplicate(?)
    # TODO make members?                        # Dim (overall dim)
    tenure_map = [2, 3, 5, 6]                   # 0
    rooms_map = [1, 2, 3, 4, 5, 6]              # 1
    occupants_map = [1, 2, 3, 4]                # 2
    bedrooms_map = [1, 2, 3, 4]                 # 3
    hhtype_map = [1, 2, 3, 4, 5]                # 4
    #
    ch_map = [1, 2]                             # 1 (5)
    buildtype_map = [2, 3, 4, 5]                # 2 (6)
    eth_map = [2, 3, 4, 5, 6, 7, 8]             # 3 (7)
    cars_map = [1, 2, 3]                        # 4 (8)
    econ_map = [1, 2, 3, 4, 5, 6, 7, 8, 9]      # 5 (9)

    tenure_rooms_occ = self.lc4404.loc[self.lc4404.GEOGRAPHY_CODE == area].copy()
    # unmap indices
    # TODO might be quicker to unmap the entire table upfront?
    Utils.unmap(tenure_rooms_occ.C_TENHUK11, tenure_map)
    Utils.unmap(tenure_rooms_occ.C_ROOMS, rooms_map)
    Utils.unmap(tenure_rooms_occ.C_SIZHUK11, occupants_map)

    m4404 = Utils.unlistify(tenure_rooms_occ,
                            ["C_TENHUK11", "C_ROOMS", "C_SIZHUK11"],
                            [len(tenure_map), len(rooms_map), len(occupants_map)],
                            "OBS_VALUE")

    tenure_beds_occ = self.lc4405.loc[self.lc4405.GEOGRAPHY_CODE == area].copy()

    # unmap indices
    Utils.unmap(tenure_beds_occ.C_BEDROOMS, rooms_map)
    Utils.unmap(tenure_beds_occ.C_TENHUK11, tenure_map)
    Utils.unmap(tenure_beds_occ.C_SIZHUK11, occupants_map)

    m4405 = Utils.unlistify(tenure_beds_occ,
                            ["C_TENHUK11", "C_BEDROOMS", "C_SIZHUK11"],
                            [len(tenure_map), len(bedrooms_map), len(occupants_map)],
                            "OBS_VALUE")

    tenure_accom = self.lc4408.loc[self.lc4408.GEOGRAPHY_CODE == area].copy()

    Utils.unmap(tenure_accom.C_TENHUK11, tenure_map)
    Utils.unmap(tenure_accom.C_AHTHUK11, hhtype_map)

    m4408 = Utils.unlistify(tenure_accom,
                            ["C_TENHUK11", "C_AHTHUK11"],
                            [len(tenure_map), len(hhtype_map)],
                            "OBS_VALUE")

    # TODO relax IPF tolerance and maxiters when used within QISI?
    p0 = humanleague.qisi(constraints, [np.array([0, 1, 2]), np.array([0, 3, 2]), np.array([0, 4])], [m4404, m4405, m4408])
    assert p0["conv"]

    tenure_ch_accom = self.lc4402.loc[self.lc4402.GEOGRAPHY_CODE == area].copy()
    Utils.unmap(tenure_ch_accom.C_CENHEATHUK11, ch_map)
    Utils.unmap(tenure_ch_accom.C_TENHUK11, tenure_map)
    Utils.unmap(tenure_ch_accom.C_TYPACCOM, buildtype_map)

    m4402 = Utils.unlistify(tenure_ch_accom,
                            ["C_TENHUK11", "C_CENHEATHUK11", "C_TYPACCOM"],
                            [len(tenure_map), len(bedrooms_map), len(occupants_map)],
                            "OBS_VALUE")

    tenure_eth_car = self.lc4202.loc[self.lc4202.GEOGRAPHY_CODE == area].copy()
    Utils.unmap(tenure_eth_car.C_ETHHUK11, eth_map)
    Utils.unmap(tenure_eth_car.C_CARSNO, cars_map)
    Utils.unmap(tenure_eth_car.C_TENHUK11, tenure_map)

    m4202 = Utils.unlistify(tenure_eth_car,
                            ["C_TENHUK11", "C_ETHHUK11", "C_CARSNO"],
                            [len(tenure_map), len(eth_map), len(cars_map)],
                            "OBS_VALUE")

    econ = self.lc4605.loc[self.lc4605.GEOGRAPHY_CODE == area].copy()
    Utils.unmap(econ.C_NSSEC, econ_map)
    Utils.unmap(econ.C_TENHUK11, tenure_map)

    # econ counts often slightly lower, need to tweak
    ##econ = Utils.adjust(econ, tenure_eth_car)

    m4605 = Utils.unlistify(econ,
                            ["C_TENHUK11", "C_NSSEC"],
                            [len(tenure_map), len(econ_map)],
                            "OBS_VALUE")

    m4605_sum = np.sum(m4605)
    m4202_sum = np.sum(m4202)

    if m4605_sum != m4202_sum:
      print("LC4605:"+str(m4605_sum)+"->"+str(m4202_sum), end="")
      tenure_4202 = np.sum(m4202, axis=(1, 2))
      nssec_4605_adj = humanleague.prob2IntFreq(np.sum(m4605, axis=0) / m4605_sum, m4202_sum)["freq"]
      m4605_adj = humanleague.qisi(m4605.astype(float), [np.array([0]), np.array([1])], [tenure_4202, nssec_4605_adj])
      if isinstance(m4605_adj, str):
        print(m4605_adj)
      assert m4605_adj["conv"]
      m4605 = m4605_adj["result"]

    # no seed constraint so just use QIS
    p1 = humanleague.qis([np.array([0, 1, 2, 3, 4]), np.array([0, 5, 6]), np.array([0, 7, 8]), np.array([0, 9])], [p0["result"], m4402, m4202, m4605])
    #p1 = humanleague.qis([np.array([0, 1, 2, 3]), np.array([0, 4, 5]), np.array([0, 6, 7])], [p0["result"], m4402, m4202])
    assert p1["conv"]

    table = humanleague.flatten(p1["result"])

    chunk = pd.DataFrame(columns=self.dwellings.columns.values)
    chunk.Area = np.repeat(area, len(table[0]))
    chunk.LC4402_C_TENHUK11 = Utils.remap(table[0], tenure_map)
    chunk.QS420EW_CELL = np.repeat(self.NOTAPPLICABLE, len(table[0]))
    chunk.LC4404EW_C_ROOMS = Utils.remap(table[1], rooms_map)
    chunk.LC4404EW_C_SIZHUK11 = Utils.remap(table[2], occupants_map)
    chunk.LC4405EW_C_BEDROOMS = Utils.remap(table[3], bedrooms_map)
    chunk.LC4408_C_AHTHUK11 = Utils.remap(table[4], hhtype_map)
    chunk.LC4402_C_CENHEATHUK11 = Utils.remap(table[5], ch_map)
    chunk.LC4402_C_TYPACCOM = Utils.remap(table[6], buildtype_map)
    chunk.CommunalSize = np.repeat(self.NOTAPPLICABLE, len(table[0]))
    chunk.LC4202EW_C_ETHHUK11 = Utils.remap(table[7], eth_map)
    chunk.LC4202EW_C_CARSNO = Utils.remap(table[8], cars_map)
    chunk.LC4605EW_C_NSSEC = Utils.remap(table[9], econ_map)
    #print(chunk.head())
    self.dwellings = self.dwellings.append(chunk, ignore_index=True)

  def __add_communal(self, area):

    # here we simply enumerate the census counts - no microsynthesis required

    area_communal = self.communal.loc[(self.communal.GEOGRAPHY_CODE == area) & (self.communal.OBS_VALUE > 0)]
    if len(area_communal) == 0:
      return

    num_communal = area_communal.OBS_VALUE.sum()

    chunk = pd.DataFrame(columns=self.dwellings.columns.values)
    chunk.Area = np.repeat(area, num_communal)
    chunk.LC4402_C_TENHUK11 = np.repeat(self.NOTAPPLICABLE, num_communal)
    chunk.LC4404EW_C_ROOMS = np.repeat(self.UNKNOWN, num_communal)
    chunk.LC4404EW_C_SIZHUK11 = np.repeat(self.UNKNOWN, num_communal)
    chunk.LC4405EW_C_BEDROOMS = np.repeat(self.UNKNOWN, num_communal)
    chunk.LC4408_C_AHTHUK11 = np.repeat(self.UNKNOWN, num_communal) # communal not considered separately to multi-person household
    chunk.LC4402_C_CENHEATHUK11 = np.repeat(2, num_communal) # assume all communal are centrally heated
    chunk.LC4402_C_TYPACCOM = np.repeat(self.NOTAPPLICABLE, num_communal)
    chunk.LC4202EW_C_ETHHUK11 = np.repeat(self.UNKNOWN, num_communal)
    chunk.LC4202EW_C_CARSNO = np.repeat(1, num_communal) # no cars (blanket assumption)

    index = 0
    #print(area, len(area_communal))
    for i in range(0, len(area_communal)):
      # average occupants per establishment - integerised (special case when zero occupants)
      establishments = area_communal.at[area_communal.index[i], "OBS_VALUE"]
      occupants = area_communal.at[area_communal.index[i], "CommunalSize"]
      if establishments == 1:
        occ_array = [occupants]
      else:
        occ_array = humanleague.prob2IntFreq(np.full(establishments, 1.0 / establishments), occupants)["freq"]
      for j in range(0, establishments):
        chunk.QS420EW_CELL.at[index] = area_communal.at[area_communal.index[i], "CELL"]
        chunk.CommunalSize.at[index] = occ_array[j]
        chunk.LC4605EW_C_NSSEC.at[index] = Utils.communal_economic_status(area_communal.at[area_communal.index[i], "CELL"])
        index += 1

    #print(chunk.head())
    self.dwellings = self.dwellings.append(chunk, ignore_index=True)

  # unoccupied, should be one entry per area
  # sample from the occupied houses
  def __add_unoccupied(self, area):
    unocc = self.ks401.loc[(self.ks401.GEOGRAPHY_CODE == area) & (self.ks401.CELL == 6)]
    assert len(unocc) == 1
    n_unocc = unocc.at[unocc.index[0], "OBS_VALUE"]
    #print(n_unocc)

    chunk = pd.DataFrame(columns=self.dwellings.columns.values)
    chunk.Area = np.repeat(area, n_unocc)
    chunk.LC4402_C_TENHUK11 = np.repeat(self.UNKNOWN, n_unocc)
    chunk.LC4404EW_C_SIZHUK11 = np.repeat(0, n_unocc)
    chunk.LC4408_C_AHTHUK11 = np.repeat(self.UNKNOWN, n_unocc)
    chunk.LC4402_C_TYPACCOM = np.repeat(self.NOTAPPLICABLE, n_unocc)
    chunk.LC4202EW_C_ETHHUK11 = np.repeat(self.UNKNOWN, n_unocc)
    chunk.LC4202EW_C_CARSNO = np.repeat(1, n_unocc) # no cars
    chunk.QS420EW_CELL = np.repeat(self.NOTAPPLICABLE, n_unocc)
    chunk.CommunalSize = np.repeat(self.NOTAPPLICABLE, n_unocc)
    chunk.LC4605EW_C_NSSEC = np.repeat(self.UNKNOWN, n_unocc)

    occ = self.dwellings.loc[(self.dwellings.Area == area) & (self.dwellings.QS420EW_CELL == self.NOTAPPLICABLE)]

    s = occ.sample(n_unocc, replace=True).reset_index()
    chunk.LC4404EW_C_ROOMS = s.LC4404EW_C_ROOMS
    chunk.LC4405EW_C_BEDROOMS = s.LC4405EW_C_BEDROOMS
    chunk.LC4402_C_CENHEATHUK11 = s.LC4402_C_CENHEATHUK11

    self.dwellings = self.dwellings.append(chunk, ignore_index=True)

  def __get_census_data(self):
    if self.region[0] == "E" or self.region[0] == "W":
      return self.__get_census_data_ew() 
    elif self.region[0] == "S":
      return self.__get_census_data_sc()
    elif self.region[0] == "N":
      raise NotImplementedError("NI census data not available") 
    else: 
      raise ValueError("invalid region code " + self.region)

  def __get_census_data_sc(self):
    #print(self.api_sc.get_metadata("LC4402SC", self.resolution))
    #print(self.api_sc.get_metadata("LC4404SC", self.resolution))

    self.lc4402 = self.api_sc.get_data("LC4402SC", self.resolution, self.region)
    self.lc4404 = self.api_sc.get_data("LC4404SC", self.resolution, self.region)

    #print(self.api_sc.get_metadata("LC4405SC", self.resolution)) not available
    #print(self.api_sc.get_metadata("LC4408SC", self.resolution)) not available
    #print(self.api_sc.get_metadata("LC1105SC", self.resolution)) not available

    # print(self.api_sc.get_metadata("LC4202SC", self.resolution))
    # print(self.api_sc.get_metadata("LC4605SC", self.resolution))
    # print(self.api_sc.get_metadata("QS420SC", self.resolution))
    # print(self.api_sc.get_metadata("QS421SC", self.resolution))

    self.ks401 = self.api_sc.get_data("KS401SC", self.resolution, self.region)
    self.lc4202 = self.api_sc.get_data("LC4202SC", self.resolution, self.region)
    self.lc4605 = self.api_sc.get_data("LC4605SC", self.resolution, self.region)

    # merge the two communal tables (so we have establishment and people counts)
    self.communal = self.api_sc.get_data("QS420SC", self.resolution, self.region)
    print(self.communal.head())
    qs421 = self.api_sc.get_data("QS421SC", self.resolution, self.region)
    communal["CommunalSize"] = qs421.OBS_VALUE

  def __get_census_data_ew(self):
    """ 
    Retrieves census tables for the specified geography
    checks for locally cached data or calls nomisweb API
    """

    # convert input string to enum
    resolution = self.api_ew.GeoCodeLookup[self.resolution]

    if self.region in self.api_ew.GeoCodeLookup.keys():
      region_codes = self.api_ew.GeoCodeLookup[self.region]
    else:
      region_codes = self.api_ew.get_lad_codes(self.region)
      if not region_codes:
        raise ValueError("no regions match the input: \"" + self.region + "\"")

    area_codes = self.api_ew.get_geo_codes(region_codes, resolution)

    # assignment does shallow copy, need to use .copy() to avoid this getting query_params fields
    common_params = {"MEASURES": "20100",
                     "date": "latest",
                     "geography": area_codes}

    # LC4402EW - Accommodation type by type of central heating in household by tenure
    query_params = common_params.copy()
    query_params["C_TENHUK11"] = "2,3,5,6"
    query_params["C_CENHEATHUK11"] = "1,2"
    query_params["C_TYPACCOM"] = "2...5"
    query_params["select"] = "GEOGRAPHY_CODE,C_TENHUK11,C_CENHEATHUK11,C_TYPACCOM,OBS_VALUE"
    self.lc4402 = self.api_ew.get_data("LC4402EW", query_params)

    # LC4404EW - Tenure by household size by number of rooms
    query_params = common_params.copy()
    query_params["C_ROOMS"] = "1...6"
    query_params["C_TENHUK11"] = "2,3,5,6"
    query_params["C_SIZHUK11"] = "1...4"
    query_params["select"] = "GEOGRAPHY_CODE,C_ROOMS,C_TENHUK11,C_SIZHUK11,OBS_VALUE"
    self.lc4404 = self.api_ew.get_data("LC4404EW", query_params)

    # LC4405EW - Tenure by household size by number of bedrooms
    query_params = common_params.copy()
    query_params["C_TENHUK11"] = "2,3,5,6"
    query_params["C_BEDROOMS"] = "1...4"
    query_params["C_SIZHUK11"] = "1...4"
    query_params["select"] = "GEOGRAPHY_CODE,C_SIZHUK11,C_TENHUK11,C_BEDROOMS,OBS_VALUE"
    self.lc4405 = self.api_ew.get_data("LC4405EW", query_params)

    # LC4408EW - Tenure by number of persons per bedroom in household by household type
    query_params = common_params.copy()
    #query_params["C_PPBROOMHEW11"] = "1...4"
    query_params["C_PPBROOMHEW11"] = "0"
    query_params["C_AHTHUK11"] = "1...5"
    query_params["C_TENHUK11"] = "2,3,5,6"
    query_params["select"] = "GEOGRAPHY_CODE,C_AHTHUK11,C_TENHUK11,OBS_VALUE"
    self.lc4408 = self.api_ew.get_data("LC4408EW", query_params)

    # LC1105EW - Residence type by sex by age
    query_params = common_params.copy()
    query_params["C_SEX"] = "0"
    query_params["C_AGE"] = "0"
    query_params["C_RESIDENCE_TYPE"] = "1,2"
    query_params["select"] = "GEOGRAPHY_CODE,C_RESIDENCE_TYPE,OBS_VALUE"
    self.lc1105 = self.api_ew.get_data("LC1105EW", query_params)

    # KS401EW - Dwellings, household spaces and accommodation type
    query_params = common_params.copy()
    query_params["RURAL_URBAN"] = "0"
    query_params["CELL"] = "5,6"
    query_params["select"] = "GEOGRAPHY_CODE,CELL,OBS_VALUE"
    self.ks401 = self.api_ew.get_data("KS401EW", query_params)

    # NOTE: common_params is passed by ref so take a copy
    self.communal = self.__get_communal_data(common_params.copy())

    # LC4202EW - Tenure by car or van availability by ethnic group of Household Reference Person (HRP)
    query_params = common_params.copy()
    query_params["C_CARSNO"] = "1...3"
    query_params["C_TENHUK11"] = "2,3,5,6"
    query_params["C_ETHHUK11"] = "2...8"
    query_params["select"] = "GEOGRAPHY_CODE,C_ETHHUK11,C_CARSNO,C_TENHUK11,OBS_VALUE"
    self.lc4202 = self.api_ew.get_data("LC4202EW", query_params)

    # LC4605EW - Tenure by NS-SeC - Household Reference Persons
    query_params = common_params.copy()
    query_params["C_TENHUK11"] = "2,3,5,6"
    query_params["C_NSSEC"] = "1...9"
    query_params["select"] = "GEOGRAPHY_CODE,C_TENHUK11,C_NSSEC,OBS_VALUE"
    self.lc4605 = self.api_ew.get_data("LC4605EW", query_params)

  def __get_communal_data(self, query_params):

    query_params["RURAL_URBAN"] = 0
    query_params["CELL"] = "2,6,11,14,22...34"
    query_params["select"] = "GEOGRAPHY_CODE,CELL,OBS_VALUE"
    # communal is qs420 plus qs421
    communal = self.api_ew.get_data("QS420EW", query_params) # establishments
    qs421 = self.api_ew.get_data("QS421EW", query_params) # people

    # merge the two tables (so we have establishment and people counts)
    communal["CommunalSize"] = qs421.OBS_VALUE
    return communal

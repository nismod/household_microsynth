""" Household ref person microsynthesis """

from random import randint
import numpy as np
import pandas as pd

import ukcensusapi.Nomisweb as Api
import humanleague
import household_microsynth.utils as Utils

class ReferencePerson:
  """ Household ref person microsynthesis """

  # Placeholders for unknown or non-applicable category values
  UNKNOWN = -1
  NOTAPPLICABLE = -2

  # initialise, supplying geographical area and resolution , plus (optionally) a location to cache downloads
  def __init__(self, region, resolution, cache_dir="./cache"):
    self.api = Api.Nomisweb(cache_dir)

    self.region = region
    # convert input string to enum
    self.resolution = resolution

    # (down)load the census tables
    self.__get_census_data()

#     # initialise table and index
#     categories = ["Area", "LC4402_C_TYPACCOM", "QS420EW_CELL", "LC4402_C_TENHUK11", "LC4408_C_AHTHUK11", "CommunalSize",
#                   "LC4404EW_C_SIZHUK11", "LC4404EW_C_ROOMS", "LC4405EW_C_BEDROOMS", "LC4408EW_C_PPBROOMHEW11",
#                   "LC4402_C_CENHEATHUK11", "LC4605EW_C_NSSEC", "LC4202EW_C_ETHHUK11", "LC4202EW_C_CARSNO"]
#     self.total_dwellings = sum(self.ks401.OBS_VALUE) + sum(self.communal.OBS_VALUE)
# #    self.dwellings = pd.DataFrame(index=range(0, self.total_dwellings), columns=categories)
#     self.dwellings = pd.DataFrame(columns=categories)
#     self.index = 0

#     # generate indices
#     self.type_index = self.lc4402.C_TYPACCOM.unique()
#     self.tenure_index = self.lc4402.C_TENHUK11.unique()
#     self.ch_index = self.lc4402.C_CENHEATHUK11.unique()
#     #self.ppb_index = self.lc4408.C_PPBROOMHEW11.unique()
#     self.comp_index = self.lc4408.C_AHTHUK11.unique()

  def run(self):
    """ run the microsynthesis """

    print(self.lc4605.head())

    area_map = self.lc4605.GEOGRAPHY_CODE.unique()

    # construct seed disallowing states where B>R]
    #                           T  R  O  B  X  (X=household type)
    constraints = np.ones([4, 6, 4, 4, 5])
    # seed from microdata...

    for area in area_map:
      print('.', end='', flush=True)

      # end area loop

  def __add_ref_persons(self, area, constraints):
    pass

  def __get_census_data(self):
    """ 
    Retrieves census tables for the specified geography
    checks for locally cached data or calls nomisweb API
    """

    # convert input string to enum
    resolution = self.api.GeoCodeLookup[self.resolution]

    if self.region in self.api.GeoCodeLookup.keys():
      region_codes = self.api.GeoCodeLookup[self.region]
    else:
      region_codes = self.api.get_lad_codes(self.region)
      if not region_codes:
        raise ValueError("no regions match the input: \"" + self.region + "\"")

    area_codes = self.api.get_geo_codes(region_codes, resolution)

    # assignment does shallow copy, need to use .copy() to avoid this getting query_params fields
    common_params = {"MEASURES": "20100",
                     "date": "latest",
                     "geography": area_codes}

    # tables:
    # LC4605 HRP: tenure by NSSEC 
    # LC4201 HRP: tenure by eth by age
    # LC6115 HRP: composition by NSSEC
    # QS111 HH: lifestage
    # LC1102 HRP: living arr by age 

    table = "LC4605"
    table_internal = "NM_1001_1"
    query_params = common_params.copy()
    query_params["C_TENHUK11"] = "2,3,5,6"
    query_params["C_NSSEC"] = "1...9"
    query_params["select"] = "GEOGRAPHY_CODE,C_NSSEC,C_TENHUK11,OBS_VALUE"
    query_params["date"] = "latest"
    query_params["MEASURES"] = "20100"
    # TODO query_params["geography"] = ...
    self.lc4605 = self.api.get_data(table, table_internal, query_params)




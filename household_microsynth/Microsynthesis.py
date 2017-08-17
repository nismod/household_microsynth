# Household microsynthesis

# Disable "Invalid constant name"
# pylint: disable=C0103

#import numpy as np
#import pandas as pd
import ukcensusapi.Nomisweb as Api
#import humanleague


# TODO come up with a class structure

class Microsynthesis:

  # initialise, supplying a location to cache downloads
  def __init__(self, cache_dir):
    self.cache_dir = cache_dir
    self.api = Api.Nomisweb(cache_dir)

  # Retrieves census tables for the specified geography
  # checks for locally cached data or calls nomisweb API
  def get_census_data(self, region, resolution):

    region_codes = self.api.get_lad_codes(region)
    area_codes = self.api.get_geo_codes(region_codes, resolution)

    # assignment does shallow copy, need to use .copy() to avoid this getting query_params fields
    common_params = {"MEASURES": "20100",
                    "date": "latest",
                    "geography": area_codes}

    # LC4402EW - Accommodation type by type of central heating in household by tenure
    table = "NM_887_1"
    query_params = common_params.copy()
    query_params["C_TENHUK11"] = "2,3,5,6"
    query_params["C_CENHEATHUK11"] = "1,2"
    query_params["C_TYPACCOM"] = "2...5"
    query_params["select"] = "GEOGRAPHY_CODE,C_TENHUK11,C_CENHEATHUK11,C_TYPACCOM,OBS_VALUE"
    LC4402 = self.api.get_data(table, query_params)

    # LC4404EW - Tenure by household size by number of rooms
    table = "NM_889_1"
    query_params = common_params.copy()
    query_params["C_ROOMS"] = "1...6"
    query_params["C_TENHUK11"] = "2,3,5,6"
    query_params["C_SIZHUK11"] = "1...4"
    query_params["select"] = "GEOGRAPHY_CODE,C_ROOMS,C_TENHUK11,C_SIZHUK11,OBS_VALUE"
    LC4404 = self.api.get_data(table, query_params)

    # LC4405EW - Tenure by household size by number of bedrooms
    table = "NM_890_1"
    query_params = common_params.copy()
    query_params["C_TENHUK11"] = "2,3,5,6"
    query_params["C_BEDROOMS"] = "1...4"
    query_params["C_SIZHUK11"] = "1...4"
    query_params["select"] = "GEOGRAPHY_CODE,C_SIZHUK11,C_TENHUK11,C_BEDROOMS,OBS_VALUE"
    LC4405 = self.api.get_data(table, query_params)

    # LC4408EW - Tenure by number of persons per bedroom in household by household type
    table = "NM_893_1"
    query_params = common_params.copy()
    query_params["C_PPBROOMHEW11"] = "1...4"
    query_params["C_AHTHUK11"] = "1...5"
    query_params["C_TENHUK11"] = "2,3,5,6"
    query_params["select"] = "GEOGRAPHY_CODE,C_PPBROOMHEW11,C_AHTHUK11,C_TENHUK11,OBS_VALUE"
    LC4408 = self.api.get_data(table, query_params)

    # LC1105EW - Residence type by sex by age
    table = "NM_1086_1"
    query_params = common_params.copy()
    query_params["C_SEX"] = "0"
    query_params["C_AGE"] = "0"
    query_params["C_RESIDENCE_TYPE"] = "1,2"
    query_params["select"] = "GEOGRAPHY_CODE,C_RESIDENCE_TYPE,OBS_VALUE"
    LC1105 = self.api.get_data(table, query_params)

    # KS401EW - Dwellings, household spaces and accommodation type
    table = "NM_618_1"
    query_params = common_params.copy()
    query_params["RURAL_URBAN"] = "0"
    query_params["CELL"] = "5,6"
    query_params["select"] = "GEOGRAPHY_CODE,CELL,OBS_VALUE"
    KS401 = self.api.get_data(table, query_params)

    # NOTE: common_params is passed by ref so take a copy
    COMMUNAL = self.__get_communal_data(common_params.copy())

    return (LC4402, LC4404, LC4405, LC4408, LC1105, KS401, COMMUNAL)

  def __get_communal_data(self, query_params):
    
    query_params["RURAL_URBAN"] = 0
    query_params["CELL"] = "2,6,11,14,22...34"
    query_params["select"] = "GEOGRAPHY_CODE,CELL,OBS_VALUE"
    QS420EW = self.api.get_data("NM_552_1", query_params) # establishments
    QS421EW = self.api.get_data("NM_553_1", query_params) # people
    
    # merge the two tables (so we have establishment and people counts)
    QS420EW["Occupants"] = QS421EW.OBS_VALUE

#    print(QS420EW.head(20))
#    print(QS421EW.head(20))

    return QS420EW

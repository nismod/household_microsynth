
# Household microsynthesis

import numpy as np
import pandas as pd
import ukcensusapi.Nomisweb as Api
import humanleague


# Retrieves census tables for the specified geography
# checks for locally cached data or calls nomisweb API
def getCensusData(region, resolution):

  api = Api.Nomisweb("./")

  regionCodes = api.getLADCodes(region)
  areaCodes = api.geoCodes(regionCodes, resolution)
  
  # assignment does shallow copy, need to use .copy() to avoid this getting queryParams fields
  commonParams = { "MEASURES": "20100",
                   "date": "latest",
                   "geography": areaCodes }

  # LC4402EW - Accommodation type by type of central heating in household by tenure
  table = "NM_887_1"  
  queryParams = commonParams.copy()
  queryParams["C_TENHUK11"] = "2,3,5,6"
  queryParams["C_CENHEATHUK11"] = "1,2"
  queryParams["C_TYPACCOM"] = "2...5"
  queryParams["select"] = "GEOGRAPHY_CODE,C_TENHUK11,C_CENHEATHUK11,C_TYPACCOM,OBS_VALUE"
  LC4402 = api.getData(table, queryParams)

  # LC4404EW - Tenure by household size by number of rooms
  table = "NM_889_1"
  queryParams = commonParams.copy()
  queryParams["C_ROOMS"] = "1...6"
  queryParams["C_TENHUK11"] = "2,3,5,6"
  queryParams["C_SIZHUK11"] = "1...4"
  queryParams["select"] = "GEOGRAPHY_CODE,C_ROOMS,C_TENHUK11,C_SIZHUK11,OBS_VALUE"
  LC4404 = api.getData(table, queryParams)

  # LC4405EW - Tenure by household size by number of bedrooms
  table = "NM_890_1"
  queryParams = commonParams.copy()
  queryParams["C_TENHUK11"] = "2,3,5,6"
  queryParams["C_BEDROOMS"] = "1...4"
  queryParams["C_SIZHUK11"] = "1...4"
  queryParams["select"] = "GEOGRAPHY_CODE,C_SIZHUK11,C_TENHUK11,C_BEDROOMS,OBS_VALUE"
  LC4405 = api.getData(table, queryParams)

  # LC4408EW - Tenure by number of persons per bedroom in household by household type
  table = "NM_893_1"
  queryParams = commonParams.copy()
  queryParams["C_PPBROOMHEW11"] = "1...4"
  queryParams["C_AHTHUK11"] = "1...5"
  queryParams["C_TENHUK11"] = "2,3,5,6"
  queryParams["select"] = "GEOGRAPHY_CODE,C_PPBROOMHEW11,C_AHTHUK11,C_TENHUK11,OBS_VALUE"
  LC4408 = api.getData(table, queryParams)

  # LC1105EW - Residence type by sex by age
  table = "NM_1086_1"
  queryParams = commonParams.copy()
  queryParams["C_SEX"] = "0"
  queryParams["C_AGE"] = "0"
  queryParams["C_RESIDENCE_TYPE"] = "1,2"
  queryParams["select"] = "GEOGRAPHY_CODE,C_RESIDENCE_TYPE,OBS_VALUE"
  LC1105EW = api.getData(table, queryParams)

  # KS401EW - Dwellings, household spaces and accommodation type
  table = "NM_618_1"
  queryParams = commonParams.copy()
  queryParams["RURAL_URBAN"] = "0"
  queryParams["CELL"] = "5,6"
  queryParams["select"] = "GEOGRAPHY_CODE,CELL,OBS_VALUE"
  KS401EW = api.getData(table, queryParams)

  return (LC4402, LC4404, LC4405, LC4408, LC1105EW, KS401EW)
  

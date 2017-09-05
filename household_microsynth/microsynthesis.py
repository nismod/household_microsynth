# Household microsynthesis

import numpy as np
import pandas as pd
import ukcensusapi.Nomisweb as Api
import humanleague
import household_microsynth.utils as Utils


# TODO come up with a class structure

class Microsynthesis:

  ## TODO this belongs in UKCensusAPI
  # static map of area types to nomis codes
  Area = {
    "LA": Api.Nomisweb.LAD,
    "MSOA": Api.Nomisweb.MSOA,
    "LSOA": Api.Nomisweb.LSOA,
    "OA": Api.Nomisweb.OA
  }

  # initialise, supplying a location to cache downloads
  def __init__(self, cache_dir):
    self.cache_dir = cache_dir
    self.api = Api.Nomisweb(cache_dir)

    # permitted states for rooms/bedrooms
    self.permitted = np.ones((6, 4))
    self.permitted[0, 1] = 0
    self.permitted[0, 2] = 0
    self.permitted[0, 3] = 0
    self.permitted[1, 2] = 0
    self.permitted[1, 3] = 0
    self.permitted[2, 3] = 0

  # 1. unconstrained usim of type and central heating 
  def step1(self, area, tenure, index, dwellings):

    thdata_raw = self.lc4402.loc[(self.lc4402.GEOGRAPHY_CODE == area) 
                  & (self.lc4402.C_TENHUK11 == tenure)
                  & (self.lc4402.OBS_VALUE != 0)]
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
  def step2(self, area, tenure, all_occupants, index, dwellings):
    for occ in all_occupants:
      rmarginal = self.lc4404[(self.lc4404.GEOGRAPHY_CODE == area) 
                        & (self.lc4404.C_TENHUK11 == tenure)
                        & (self.lc4404.C_SIZHUK11 == occ)].OBS_VALUE.as_matrix()
      bmarginal = self.lc4405[(self.lc4405.GEOGRAPHY_CODE == area) 
                        & (self.lc4405.C_TENHUK11 == tenure)
                        & (self.lc4405.C_SIZHUK11 == occ)].OBS_VALUE.as_matrix()

      usim = humanleague.synthPopG(rmarginal, bmarginal, self.permitted)
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
        dwellings.at[index, "PPerBed"] = Utils.people_per_bedroom(occ, pop[1][i] + 1)
        index += 1
    return index

  # 3. "usim" of composition vs personsPerBedroom
  def step3(self, area, tenure, dwellings):
    # single are unambiguous
    dwellings.ix[(dwellings.Area == area)
            & (dwellings.Tenure == tenure)
            & (dwellings.Occupants == 1), "Composition"] = 1

    # randomly assign the rest (see below)
    compdata_raw = self.lc4408.loc[(self.lc4408.GEOGRAPHY_CODE == area)
                        & (self.lc4408.C_TENHUK11 == tenure)
                        & (self.lc4408.C_AHTHUK11 != 1)
                        & (self.lc4408.OBS_VALUE > 0)]

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

  def add_communal(self, area, index, dwellings):
    area_communal = self.communal.loc[(self.communal.GEOGRAPHY_CODE == area) & (self.communal.OBS_VALUE > 0)]

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
    return index


  # unoccupied, should be one entry per area
  # microsynthesise the occupied houses by BuildType, Tenure, CentralHeating and sample the unoccupied from this dwellings
  def add_unoccupied(self, area, type_index, tenure_index, ch_index, index, dwellings):
    unocc = self.ks401.loc[(self.ks401.GEOGRAPHY_CODE == area) & (self.ks401.CELL == 6)]
    assert len(unocc == 1)
    n_unocc = unocc.at[unocc.index[0], "OBS_VALUE"]

    if n_unocc:
      # type marginal
      type_tenure_ch = self.lc4402.loc[self.lc4402.GEOGRAPHY_CODE == area]
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
    return index

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
    self.lc4402 = self.api.get_data("LC4402EW", table, query_params)

    # LC4404EW - Tenure by household size by number of rooms
    table = "NM_889_1"
    query_params = common_params.copy()
    query_params["C_ROOMS"] = "1...6"
    query_params["C_TENHUK11"] = "2,3,5,6"
    query_params["C_SIZHUK11"] = "1...4"
    query_params["select"] = "GEOGRAPHY_CODE,C_ROOMS,C_TENHUK11,C_SIZHUK11,OBS_VALUE"
    self.lc4404 = self.api.get_data("LC4404EW", table, query_params)

    # LC4405EW - Tenure by household size by number of bedrooms
    table = "NM_890_1"
    query_params = common_params.copy()
    query_params["C_TENHUK11"] = "2,3,5,6"
    query_params["C_BEDROOMS"] = "1...4"
    query_params["C_SIZHUK11"] = "1...4"
    query_params["select"] = "GEOGRAPHY_CODE,C_SIZHUK11,C_TENHUK11,C_BEDROOMS,OBS_VALUE"
    self.lc4405 = self.api.get_data("LC4405EW", table, query_params)

    # LC4408EW - Tenure by number of persons per bedroom in household by household type
    table = "NM_893_1"
    query_params = common_params.copy()
    query_params["C_PPBROOMHEW11"] = "1...4"
    query_params["C_AHTHUK11"] = "1...5"
    query_params["C_TENHUK11"] = "2,3,5,6"
    query_params["select"] = "GEOGRAPHY_CODE,C_PPBROOMHEW11,C_AHTHUK11,C_TENHUK11,OBS_VALUE"
    self.lc4408 = self.api.get_data("LC4408EW", table, query_params)

    # LC1105EW - Residence type by sex by age
    table = "NM_1086_1"
    query_params = common_params.copy()
    query_params["C_SEX"] = "0"
    query_params["C_AGE"] = "0"
    query_params["C_RESIDENCE_TYPE"] = "1,2"
    query_params["select"] = "GEOGRAPHY_CODE,C_RESIDENCE_TYPE,OBS_VALUE"
    self.lc1105 = self.api.get_data("LC1105EW", table, query_params)

    # KS401EW - Dwellings, household spaces and accommodation type
    table = "NM_618_1"
    query_params = common_params.copy()
    query_params["RURAL_URBAN"] = "0"
    query_params["CELL"] = "5,6"
    query_params["select"] = "GEOGRAPHY_CODE,CELL,OBS_VALUE"
    self.ks401 = self.api.get_data("KS401EW", table, query_params)

    # NOTE: common_params is passed by ref so take a copy
    self.__get_communal_data(common_params.copy())

    # LC4202EW - Tenure by car or van availability by ethnic group of Household Reference Person (HRP)
    table = "NM_880_1"
    query_params = common_params.copy()
    query_params["C_CARSNO"] = "1..3"
    query_params["C_TENHUK11"] = "2,3,5,6"
    query_params["C_ETHHUK11"] = "2...8"
    query_params["select"] = "GEOGRAPHY_CODE,C_ETHHUK11,C_CARSNO,C_TENHUK11,OBS_VALUE"
    # TODO query_params["geography"] = ...
    self.lc4202 = self.api.get_data("LC4202EW", table, query_params)

    # LC4601EW - Tenure by economic activity by age - Household Reference Persons
    table = "NM_899_1"
    query_params = common_params.copy()
    query_params["C_TENHUK11"] = "2,3,5,6"
    query_params["C_ECOPUK11"] = "4,5,7,8,9,11,12,14...18"
    query_params["C_AGE"] = "0"
    query_params["select"] = "GEOGRAPHY_CODE,C_TENHUK11,C_ECOPUK11,OBS_VALUE"
    # TODO query_params["geography"] = ...
    self.lc4601 = self.api.get_data("LC4601EW", table, query_params)

  def __get_communal_data(self, query_params):

    query_params["RURAL_URBAN"] = 0
    query_params["CELL"] = "2,6,11,14,22...34"
    query_params["select"] = "GEOGRAPHY_CODE,CELL,OBS_VALUE"
    # communal is qs420 plus qs421
    self.communal = self.api.get_data("QS420EW", "NM_552_1", query_params) # establishments
    qs421 = self.api.get_data("QS421EW", "NM_553_1", query_params) # people

    # merge the two tables (so we have establishment and people counts)
    self.communal["Occupants"] = qs421.OBS_VALUE
    


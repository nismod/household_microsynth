# Household microsynthesis

import numpy as np
import pandas as pd
import ukcensusapi.Nomisweb as Api
import humanleague
import household_microsynth.utils as Utils

class Microsynthesis:

  # Placeholders for unknown or non-applicable category values
  UNKNOWN = -1
  NOTAPPLICABLE = -2

  # initialise, supplying geographical area and resolution , plus (optionally) a location to cache downloads
  def __init__(self, region, resolution, cache_dir="./cache"):
    self.api = Api.Nomisweb(cache_dir)

    # permitted states for rooms/bedrooms
    self.permitted = np.ones((6, 4))
    self.permitted[0, 1] = 0
    self.permitted[0, 2] = 0
    self.permitted[0, 3] = 0
    self.permitted[1, 2] = 0
    self.permitted[1, 3] = 0
    self.permitted[2, 3] = 0

    self.region = region
    # convert input string to enum
    self.resolution = resolution

    # (down)load the census tables
    self.__get_census_data()

    # initialise table and index
    categories = ["Area", "LC4402_C_TYPACCOM", "QS420EW_CELL", "LC4402_C_TENHUK11", "LC4408_C_AHTHUK11", "CommunalSize",
                  "LC4404EW_C_SIZHUK11", "LC4404EW_C_ROOMS", "LC4405EW_C_BEDROOMS", "LC4408EW_C_PPBROOMHEW11",
                  "LC4402_C_CENHEATHUK11", "LC4601EW_C_ECOPUK11", "LC4202EW_C_ETHHUK11", "LC4202EW_C_CARSNO"]
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

  # run the microsynthesis
  def run(self):
    all_areas = self.lc4402.GEOGRAPHY_CODE.unique()
    all_tenures = self.lc4402.C_TENHUK11.unique() # assumes same as msynth.lc4404/5.C_TENHUK11
    all_occupants = self.lc4404.C_SIZHUK11.unique() # assumes same as msynth.lc4405.C_SIZHUK11

    for area in all_areas:
      print('.', end='', flush=True)
      for tenure in self.tenure_index:

        # 1. unconstrained usim of type and central heating
        self.__step1(area, tenure)

        # 2. constrained usim of rooms and bedrooms
        self.__step2(area, tenure, all_occupants)

        # 3. "usim" of composition vs personsPerBedroom
        self.__step3(area, tenure)

      # end tenure loop

      # add communal residences
      self.__add_communal(area)

      # add unoccupied properties
      self.__add_unoccupied(area)

      # adds rooms and beds based on same dist as occupied households in same area and type
      self.__add_unoccupied_detail(area)

      # end area loop

  # run the microsynthesis
  def run2(self):
    #                                           DIM
    area_map = self.lc4404.GEOGRAPHY_CODE.unique() 

    # construct seed disallowing states where B>R]
    #                           T  R  O  B  X  (X=household type)
    self.constraints = np.ones([4, 6, 4, 4, 5])
    # forbid bedrooms>rooms
    for r in range(0,6): # use rooms/beds map sizes
      for b in range(r+1,4):
        self.constraints[:,r,:,b,:] = 0
    # constrain single person household to occupants=1
    self.constraints[:,:,0,:,1] = 0
    self.constraints[:,:,0,:,2] = 0
    self.constraints[:,:,0,:,3] = 0
    self.constraints[:,:,0,:,4] = 0
    self.constraints[:,:,1,:,0] = 0
    self.constraints[:,:,2,:,0] = 0
    self.constraints[:,:,3,:,0] = 0

    for area in area_map:
      print('.', end='', flush=True)

      # 1. households
      self.__add_households(area)

      # # add communal residences
      # self.__add_communal(area)

      # # add unoccupied properties
      # self.__add_unoccupied(area)

      # # adds rooms and beds based on same dist as occupied households in same area and type
      # self.__add_unoccupied_detail(area)

      # end area loop
    self.dwellings.to_csv("./hh.csv")


  def __add_households(self, area):

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
    econ_map = [4,5,7,8,9,11,12,14,15,16,17,18] # 5 (9)

    tenure_rooms_occ = self.lc4404.loc[self.lc4404.GEOGRAPHY_CODE == area].copy()
    # unmap indices
    # TODO might be quicker to unmap the entire table upfront?
    Utils.unmap(tenure_rooms_occ.C_TENHUK11, tenure_map)
    Utils.unmap(tenure_rooms_occ.C_ROOMS, rooms_map)
    Utils.unmap(tenure_rooms_occ.C_SIZHUK11, occupants_map)

    m4404 = Utils.unlistify(tenure_rooms_occ, 
                            ["C_TENHUK11","C_ROOMS","C_SIZHUK11"], 
                            [len(tenure_map),len(rooms_map),len(occupants_map)], 
                            "OBS_VALUE")

    tenure_beds_occ = self.lc4405.loc[self.lc4405.GEOGRAPHY_CODE == area].copy()

    # unmap indices
    Utils.unmap(tenure_beds_occ.C_BEDROOMS, rooms_map)
    Utils.unmap(tenure_beds_occ.C_TENHUK11, tenure_map)
    Utils.unmap(tenure_beds_occ.C_SIZHUK11, occupants_map)

    m4405 = Utils.unlistify(tenure_beds_occ,
                            ["C_TENHUK11","C_BEDROOMS","C_SIZHUK11"],
                            [len(tenure_map),len(bedrooms_map),len(occupants_map)],
                            "OBS_VALUE")

    tenure_accom = self.lc4408.loc[self.lc4408.GEOGRAPHY_CODE == area].copy()

    Utils.unmap(tenure_accom.C_TENHUK11, tenure_map)
    Utils.unmap(tenure_accom.C_AHTHUK11, hhtype_map)

    m4408 = Utils.unlistify(tenure_accom,
                            ["C_TENHUK11","C_AHTHUK11"],
                            [len(tenure_map),len(hhtype_map)],
                            "OBS_VALUE")

    # TODO relax IPF tolerance and maxiters when used within QISI?
    p0 = humanleague.qisi(self.constraints, [np.array([0,1,2]), np.array([0,3,2]), np.array([0,4])], [m4404, m4405, m4408])
    assert p0["conv"]

    tenure_ch_accom = self.lc4402.loc[self.lc4402.GEOGRAPHY_CODE == area].copy()
    Utils.unmap(tenure_ch_accom.C_CENHEATHUK11, ch_map)
    Utils.unmap(tenure_ch_accom.C_TENHUK11, tenure_map)
    Utils.unmap(tenure_ch_accom.C_TYPACCOM, buildtype_map)

    m4402 = Utils.unlistify(tenure_ch_accom,
                            ["C_TENHUK11","C_CENHEATHUK11","C_TYPACCOM"],
                            [len(tenure_map),len(bedrooms_map),len(occupants_map)],
                            "OBS_VALUE")

    tenure_eth_car = self.lc4202.loc[self.lc4202.GEOGRAPHY_CODE == area].copy()
    Utils.unmap(tenure_eth_car.C_ETHHUK11, eth_map)
    Utils.unmap(tenure_eth_car.C_CARSNO, cars_map)
    Utils.unmap(tenure_eth_car.C_TENHUK11, tenure_map)

    m4202 = Utils.unlistify(tenure_eth_car,
                            ["C_TENHUK11","C_ETHHUK11","C_CARSNO"],
                            [len(tenure_map),len(eth_map),len(cars_map)],
                            "OBS_VALUE")

    econ = self.lc4601.loc[self.lc4601.GEOGRAPHY_CODE == area].copy()
    Utils.unmap(econ.C_ECOPUK11, econ_map)
    Utils.unmap(econ.C_TENHUK11, tenure_map)

    # econ counts often slightly lower, need to tweak
    econ = Utils.adjust(econ, tenure_eth_car)

    m4601 = Utils.unlistify(econ,
                            ["C_TENHUK11","C_ECOPUK11"],
                            [len(tenure_map),len(econ_map)],
                            "OBS_VALUE")

    # no seed constraint so just use QIS
    p1 = humanleague.qis([np.array([0, 1, 2, 3, 4]), np.array([0, 5, 6]), np.array([0, 7, 8]), np.array([0, 9])], [p0["result"], m4402, m4202, m4601])
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
    chunk.LC4601EW_C_ECOPUK11 = Utils.remap(table[9], econ_map)
    #print(chunk.head())
    self.dwellings = self.dwellings.append(chunk)

    # categories = ["Area", "LC4402_C_TYPACCOM", "QS420EW_CELL", "LC4402_C_TENHUK11", "LC4408_C_AHTHUK11", "CommunalSize",
    #               "LC4404EW_C_SIZHUK11", "LC4404EW_C_ROOMS", "LC4405EW_C_BEDROOMS", "LC4408EW_C_PPBROOMHEW11",
    #               "LC4402_C_CENHEATHUK11", "LC4601EW_C_ECOPUK11", "LC4202EW_C_ETHHUK11", "LC4202EW_C_CARSNO"]

  # 1. unconstrained usim of type and central heating
  def __step1(self, area, tenure):

    thdata_raw = self.lc4402.loc[(self.lc4402.GEOGRAPHY_CODE == area)
                               & (self.lc4402.C_TENHUK11 == tenure)
                               & (self.lc4402.OBS_VALUE != 0)]
    #print(area)
    #print(thdata_raw)
    thdata = np.vstack((np.repeat(thdata_raw.C_TYPACCOM.as_matrix(), thdata_raw.OBS_VALUE.as_matrix()),
                        np.repeat(thdata_raw.C_CENHEATHUK11.as_matrix(), thdata_raw.OBS_VALUE.as_matrix()))).T

    # randomise to eliminate bias w.r.t. occupants/rooms/bedrooms
    np.random.shuffle(thdata)

    ethcar_raw = self.lc4202.loc[(self.lc4202.GEOGRAPHY_CODE == area)
                               & (self.lc4202.C_TENHUK11 == tenure)
                               & (self.lc4202.OBS_VALUE != 0)]
    #print(thdata_raw)
    ethcar = np.vstack((np.repeat(ethcar_raw.C_ETHHUK11.as_matrix(), ethcar_raw.OBS_VALUE.as_matrix()),
                        np.repeat(ethcar_raw.C_CARSNO.as_matrix(), ethcar_raw.OBS_VALUE.as_matrix()))).T
    # randomise to eliminate bias w.r.t. occupants/rooms/bedrooms
    np.random.shuffle(ethcar)


    econ_raw = self.lc4601.loc[(self.lc4601.GEOGRAPHY_CODE == area)
                               & (self.lc4601.C_TENHUK11 == tenure)
                               & (self.lc4601.OBS_VALUE != 0)]
    econ = np.repeat(econ_raw.C_ECOPUK11.as_matrix(), econ_raw.OBS_VALUE.as_matrix())
    np.random.shuffle(econ)

    if len(thdata) != len(econ):
      print("WARNING: %s, tenure %s EconStatus mismatch: %d vs %d" % (area, tenure, len(thdata), len(econ)))


    subindex = self.index
    # TODO vectorise
    for i in range(0, len(thdata)):
      self.dwellings.at[subindex, "LC4402_C_TYPACCOM"] = thdata[i][0]
      self.dwellings.at[subindex, "LC4402_C_CENHEATHUK11"] = thdata[i][1]
      # workaround for fact that there are sometimes fewer entries for economic status
      self.dwellings.at[subindex, "LC4601EW_C_ECOPUK11"] = econ[i % len(econ)]
      self.dwellings.at[subindex, "LC4202EW_C_ETHHUK11"] = ethcar[i][0]
      self.dwellings.at[subindex, "LC4202EW_C_CARSNO"] = ethcar[i][1]
      subindex += 1

  # 2. constrained usim of rooms and bedrooms
  def __step2(self, area, tenure, all_occupants):
    for occ in all_occupants:
      rmarginal = self.lc4404.loc[(self.lc4404.GEOGRAPHY_CODE == area)
                                & (self.lc4404.C_TENHUK11 == tenure)
                                & (self.lc4404.C_SIZHUK11 == occ)].OBS_VALUE.as_matrix()
      bmarginal = self.lc4405.loc[(self.lc4405.GEOGRAPHY_CODE == area)
                                & (self.lc4405.C_TENHUK11 == tenure)
                                & (self.lc4405.C_SIZHUK11 == occ)].OBS_VALUE.as_matrix()

      usim = humanleague.synthPopG(rmarginal, bmarginal, self.permitted)
      pop = usim["result"]
      assert usim["conv"]
      #print(len(pop[0]))
      for i in range(0, len(pop[0])):
        # TODO why does moving this to above break consistency checks?
        self.dwellings.at[self.index, "Area"] = area
        # Household has no communal category
        self.dwellings.at[self.index, "QS420EW_CELL"] = self.NOTAPPLICABLE
        self.dwellings.at[self.index, "LC4402_C_TENHUK11"] = tenure
        self.dwellings.at[self.index, "LC4404EW_C_SIZHUK11"] = occ
        self.dwellings.at[self.index, "CommunalSize"] = self.NOTAPPLICABLE
        self.dwellings.at[self.index, "LC4404EW_C_ROOMS"] = pop[0][i] + 1 # since "0" means 1 room
        self.dwellings.at[self.index, "LC4405EW_C_BEDROOMS"] = pop[1][i] + 1
        self.dwellings.at[self.index, "LC4408EW_C_PPBROOMHEW11"] = Utils.people_per_bedroom(occ, pop[1][i] + 1)
        self.index += 1


  # 3. "usim" of composition vs personsPerBedroom
  def __step3(self, area, tenure):
    # single are unambiguous
    self.dwellings.ix[(self.dwellings.Area == area)
                    & (self.dwellings.LC4402_C_TENHUK11 == tenure)
                    & (self.dwellings.LC4404EW_C_SIZHUK11 == 1), "LC4408_C_AHTHUK11"] = 1

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

    if n_not_single != len(self.dwellings[(self.dwellings.Area == area)
                                  & (self.dwellings.LC4402_C_TENHUK11 == tenure)
                                  & (self.dwellings.LC4408_C_AHTHUK11 != 1)]):
      print("Composition mismatch:", area, tenure, n_not_single, "vs", len(self.dwellings[(self.dwellings.Area == area)
                                                                        & (self.dwellings.LC4402_C_TENHUK11 == tenure)
                                                                        & (self.dwellings.LC4408_C_AHTHUK11 != 1)]))
    else:
      #print(compdata[:,0])
      self.dwellings.ix[(self.dwellings.Area == area)
                  & (self.dwellings.LC4402_C_TENHUK11 == tenure)
                  & (self.dwellings.LC4408_C_AHTHUK11 != 1), "LC4408_C_AHTHUK11"] = compdata[:, 1]
#        dwellings.ix[(dwellings.Area == area)
#                    & (dwellings.LC4402_C_TENHUK11 == tenure)
#                    & (dwellings.LC4408_C_AHTHUK11 != 1), "LC4408EW_C_PPBROOMHEW11"] = compdata[:,0]

  def __add_communal(self, area):
    area_communal = self.communal.loc[(self.communal.GEOGRAPHY_CODE == area) & (self.communal.OBS_VALUE > 0)]

    #print(area, len(area_communal))
    for i in range(0, len(area_communal)):
      # average occupants per establishment - integerised (special case when zero occupants)
      establishments = area_communal.at[area_communal.index[i], "OBS_VALUE"]

      occupants = area_communal.at[area_communal.index[i], "LC4404EW_C_SIZHUK11"]
      # TODO pemit zero dwellings in prob2IntFreq to avoid this branch
      if occupants:
        occ_array = humanleague.prob2IntFreq(np.full(establishments, 1.0 / establishments), occupants)["freq"]
      else:
        occ_array = np.zeros(establishments)
      #print(occ_array)

      # row indices are the original values from the entire table
      for j in range(0, establishments):
        self.dwellings.at[self.index, "Area"] = area
        self.dwellings.at[self.index, "LC4402_C_TYPACCOM"] = self.NOTAPPLICABLE
        # TODO check j is correct index? (R code uses i)
        self.dwellings.at[self.index, "QS420EW_CELL"] = area_communal.at[area_communal.index[i], "CELL"]
        self.dwellings.at[self.index, "LC4402_C_TENHUK11"] = self.NOTAPPLICABLE
        self.dwellings.at[self.index, "LC4404EW_C_SIZHUK11"] = self.UNKNOWN
        self.dwellings.at[self.index, "CommunalSize"] = occ_array[j]
        # TODO if zero occupants, how to set rooms/beds? mean value of establishment type in region?
        self.dwellings.at[self.index, "LC4404EW_C_ROOMS"] = self.UNKNOWN
        self.dwellings.at[self.index, "LC4405EW_C_BEDROOMS"] = self.UNKNOWN
        self.dwellings.at[self.index, "LC4408_C_AHTHUK11"] = 5 # communal implies multi-person household
        self.dwellings.at[self.index, "LC4408EW_C_PPBROOMHEW11"] = 2 # 1-1.5
        self.dwellings.at[self.index, "LC4402_C_CENHEATHUK11"] = 2 # assume all communal are centrally heated
        # use a lookup based on establishment type
        self.dwellings.at[self.index, "LC4601EW_C_ECOPUK11"] = Utils.communal_economic_status(area_communal.at[area_communal.index[i], "CELL"])
        self.dwellings.at[self.index, "LC4202EW_C_ETHHUK11"] = 5 # mixed/multiple
        self.dwellings.at[self.index, "LC4202EW_C_CARSNO"] = 1 # no cars (blanket assumption)
        self.index += 1

  # unoccupied, should be one entry per area
  # microsynthesise the occupied houses by BuildType, Tenure, CentralHeating and sample the unoccupied from this dwellings
  def __add_unoccupied(self, area):
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
      assert uusim["conv"]
      # randomly sample n_unocc values
      occ_pop = pd.DataFrame(np.array(uusim["result"]).T, columns=["LC4402_C_TYPACCOM", "LC4402_C_TENHUK11", "LC4402_C_CENHEATHUK11"])
      # use without-replacement sampling if possible
      unocc_pop = occ_pop.sample(n=n_unocc, replace=len(occ_pop) < n_unocc)
      # we now potentially have duplicate index values which can cause problems indexing
#      print(unocc_pop.head(10))
      unocc_pop = unocc_pop.reset_index(drop=True)
#      print(unocc_pop.head(10))

      for j in range(0, n_unocc):
        self.dwellings.at[self.index, "Area"] = area
        self.dwellings.at[self.index, "LC4402_C_TYPACCOM"] = self.type_index[unocc_pop.at[j, "LC4402_C_TYPACCOM"]]
        self.dwellings.at[self.index, "QS420EW_CELL"] = self.NOTAPPLICABLE
        self.dwellings.at[self.index, "LC4402_C_TENHUK11"] = self.tenure_index[unocc_pop.at[j, "LC4402_C_TENHUK11"]]
        self.dwellings.at[self.index, "LC4404EW_C_SIZHUK11"] = 0
        self.dwellings.at[self.index, "CommunalSize"] = self.NOTAPPLICABLE
#        # Rooms/beds are done at the end (so we can sample dwellings)
        self.dwellings.at[self.index, "LC4404EW_C_ROOMS"] = 0
        self.dwellings.at[self.index, "LC4405EW_C_BEDROOMS"] = 0
        self.dwellings.at[self.index, "LC4408_C_AHTHUK11"] = self.UNKNOWN
        self.dwellings.at[self.index, "LC4408EW_C_PPBROOMHEW11"] = 1
        self.dwellings.at[self.index, "LC4402_C_CENHEATHUK11"] = self.ch_index[unocc_pop.at[j, "LC4402_C_CENHEATHUK11"]]
        self.dwellings.at[self.index, "LC4601EW_C_ECOPUK11"] = self.UNKNOWN
        self.dwellings.at[self.index, "LC4202EW_C_ETHHUK11"] = self.UNKNOWN
        self.dwellings.at[self.index, "LC4202EW_C_CARSNO"] = 1 # no cars (no people)
        self.index += 1

  # rooms and beds for unoccupied (sampled from occupied population in same area and same BuildType)
  # TODO this is highly suboptimal, subsetting the same thing over and over again
  def __add_unoccupied_detail(self, area):

    for t in self.type_index:
      # get unoccupied dwellings
      unocc = self.dwellings.loc[(self.dwellings.Area == area)
                               & (self.dwellings.LC4402_C_TYPACCOM == t)
                               & (self.dwellings.LC4408_C_AHTHUK11 == self.UNKNOWN)]
      nunocc = len(unocc)
      if nunocc == 0:
        continue

      # sample (with repl) from all occupied dwellings of same build type in same area
      sample = self.dwellings.loc[(self.dwellings.Area == area) 
                                & (self.dwellings.LC4402_C_TYPACCOM == t) 
                                & (self.dwellings.LC4408_C_AHTHUK11 != self.UNKNOWN)].sample(len(unocc), replace=True)
      # repeated index values cause problems
      sample = sample.reset_index(drop=True)
      j = 0
      for i in unocc.index: 
        #assert len(sample)
        r = sample.at[sample.index[j], "LC4404EW_C_ROOMS"]
        b = sample.at[sample.index[j], "LC4405EW_C_BEDROOMS"]

        self.dwellings.at[i, "LC4404EW_C_ROOMS"] = r
        self.dwellings.at[i, "LC4405EW_C_BEDROOMS"] = b 
        j = j + 1

  # Retrieves census tables for the specified geography
  # checks for locally cached data or calls nomisweb API
  def __get_census_data(self):

    # convert input string to enum
    resolution = self.api.GeoCodeLookup[self.resolution]

    if self.region in self.api.GeoCodeLookup.keys():
      region_codes = self.api.GeoCodeLookup[self.region]
    else:
      region_codes = self.api.get_lad_codes(self.region)
      if not len(region_codes):
        raise ValueError("no regions match the input: \"" + region + "\"")

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
    #query_params["C_PPBROOMHEW11"] = "1...4"
    query_params["C_PPBROOMHEW11"] = "0"
    query_params["C_AHTHUK11"] = "1...5"
    query_params["C_TENHUK11"] = "2,3,5,6"
    ##query_params["select"] = "GEOGRAPHY_CODE,C_PPBROOMHEW11,C_AHTHUK11,C_TENHUK11,OBS_VALUE"
    query_params["select"] = "GEOGRAPHY_CODE,C_AHTHUK11,C_TENHUK11,OBS_VALUE"
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
    query_params["C_CARSNO"] = "1...3"
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
    self.communal["LC4404EW_C_SIZHUK11"] = qs421.OBS_VALUE
    


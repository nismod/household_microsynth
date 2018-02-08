""" Household ref person microsynthesis """

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

    # initialise table and index
    categories = ["Area", "LC4605_C_NSSEC", "LC4605_C_TENHUK11", "LC4201_C_AGE", "LC4201_C_ETHPUK11",
                  "QS111_C_HHLSHUK11", "LC1102_C_LARPUK11"]

    # LC4605_C_NSSEC  LC4605_C_TENHUK11
    # LC4201_C_AGE  LC4201_C_ETHPUK11  [C_TENHUK11]
    # QS111_C_HHLSHUK11
    # [C_AGE] LC1102_C_LARPUK11

    self.num_hrps = sum(self.lc4605.OBS_VALUE)
    self.hrps = pd.DataFrame(columns=categories)
    self.index = 0

#     # generate indices
    self.nssec_index = self.lc4605.C_NSSEC.unique()
    self.tenure_index = self.lc4605.C_TENHUK11.unique()
    self.age_index = self.lc4201.C_AGE.unique()
    self.eth_index = self.lc4201.C_ETHPUK11.unique() # how come not C_ETHHUK11?
    self.lifestage_index = self.qs111.C_HHLSHUK11.unique()
    self.livarr_index = self.lc1102.C_LARPUK11.unique()

  def run(self):
    """ run the microsynthesis """

    # print(self.nssec_index)
    # print(self.tenure_index)
    # print(self.age_index)
    # print(self.eth_index)
    # print(self.lifestage_index)
    # print(self.livarr_index)

    area_map = self.lc4605.GEOGRAPHY_CODE.unique()

    # construct seed disallowing states where lifestage doesn match age
    #                      N  T  A  E   L  V   (V=living arrangements)
    # use microdata here if possible
    constraints = np.ones([9, 4, 4, 7, 12, 7])
    # seed from microdata...

    for area in area_map:
      print('.', end='', flush=True)

      self.__add_ref_persons(area, constraints)

      # end area loop

  def __add_ref_persons(self, area, constraints):

    nssec_tenure = self.lc4605.loc[self.lc4605.GEOGRAPHY_CODE == area].copy()
    # unmap indices
    # TODO might be quicker to unmap the entire table upfront?
    Utils.unmap(nssec_tenure.C_NSSEC, self.nssec_index)
    Utils.unmap(nssec_tenure.C_TENHUK11, self.tenure_index)

    m4605 = Utils.unlistify(nssec_tenure,
                            ["C_NSSEC", "C_TENHUK11"],
                            [len(self.nssec_index), len(self.tenure_index)],
                            "OBS_VALUE")
    #print(m4605)

    age_eth_tenure = self.lc4201.loc[self.lc4201.GEOGRAPHY_CODE == area].copy()
    # unmap indices
    # TODO might be quicker to unmap the entire table upfront?
    #Utils.unmap(age_eth_tenure.C_AGE, self.age_index)
    Utils.unmap(age_eth_tenure.C_ETHPUK11, self.eth_index)
    Utils.unmap(age_eth_tenure.C_TENHUK11, self.tenure_index)

    m4201 = Utils.unlistify(age_eth_tenure,
                            ["C_AGE", "C_ETHPUK11", "C_TENHUK11"],
                            [len(self.age_index), len(self.eth_index), len(self.tenure_index)],
                            "OBS_VALUE")
    # collapse age
    m4201 = np.sum(m4201, axis=0)

    # now check LC4605 total matches LC4201 and adjust as necessary (ensuring partial sum in tenure dimension is preserved)
    m4605_sum = np.sum(m4605)
    m4201_sum = np.sum(m4201)
    if m4605_sum != m4201_sum:
      print("LC4605:"+str(m4605_sum)+"->"+str(m4201_sum), end="")
      tenure_4201 = np.sum(m4201, axis=0)
      nssec_4605_adj = humanleague.prob2IntFreq(np.sum(m4605, axis=1) / m4605_sum, m4201_sum)["freq"]
      #print(m4605)
      m4605_adj = humanleague.qisi(m4605.astype(float), [np.array([0]), np.array([1])], [nssec_4605_adj, tenure_4201])
      if isinstance(m4605_adj, str):
        print(m4605_adj)
      assert m4605_adj["conv"]
      m4605 = m4605_adj["result"]
      #print(m4605)

    lifestage = self.qs111.loc[self.qs111.GEOGRAPHY_CODE == area].copy()
    # unmap indices
    # TODO might be quicker to unmap the entire table upfront?
    Utils.unmap(lifestage.C_HHLSHUK11, self.lifestage_index)

    mq111 = Utils.unlistify(lifestage,
                            ["C_HHLSHUK11"],
                            [len(self.lifestage_index)],
                            "OBS_VALUE")
    #mq111 = lifestage.OBS_VALUE
    #print(mq111)

    age_livarr = self.lc1102.loc[self.lc1102.GEOGRAPHY_CODE == area].copy()

    # unmap indices
    # TODO might be quicker to unmap the entire table upfront?
    Utils.unmap(age_livarr.C_AGE, self.age_index)
    Utils.unmap(age_livarr.C_LARPUK11, self.livarr_index)

    # # TODO resolve age band incompatibility issues
    # m1102 = Utils.unlistify(age_livarr,
    #                         ["C_AGE", "C_LARPUK11"],
    #                         [len(self.age_index) + 1, len(self.livarr_index)],
    #                         "OBS_VALUE")
    # m1102 = age_livarr.groupby("C_LARPUK11")["OBS_VALUE"].sum().as_matrix()
    m1102 = Utils.unlistify(age_livarr,
                            ["C_LARPUK11"],
                            [len(self.livarr_index)],
                            "OBS_VALUE")
    #print(m1102)

    pop = humanleague.qis([np.array([0, 1]), np.array([2, 1]), np.array([3]), np.array([4])], [m4605, m4201, mq111, m1102])
    if isinstance(pop, str):
      print(pop)
    assert pop["conv"]

    table = humanleague.flatten(pop["result"])

    chunk = pd.DataFrame(columns=self.hrps.columns.values)
    chunk.Area = np.repeat(area, len(table[0]))
    chunk.LC4605_C_NSSEC = Utils.remap(table[0], self.nssec_index)
    chunk.LC4605_C_TENHUK11 = Utils.remap(table[1], self.tenure_index)
    chunk.LC4201_C_ETHPUK11 = Utils.remap(table[2], self.eth_index)
    chunk.QS111_C_HHLSHUK11 = Utils.remap(table[3], self.lifestage_index)
    chunk.LC1102_C_LARPUK11 = Utils.remap(table[4], self.livarr_index)
    #print(chunk.head())
    self.hrps = self.hrps.append(chunk)

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

    # LC4605EW Tenure by NS-SeC - Household Reference Persons
    table = "NM_1001_1"
    query_params = common_params.copy()
    query_params["C_TENHUK11"] = "2,3,5,6"
    query_params["C_NSSEC"] = "1...9"
    query_params["select"] = "GEOGRAPHY_CODE,C_NSSEC,C_TENHUK11,OBS_VALUE"
    self.lc4605 = self.api.get_data("LC4605EW", table, query_params)
    #self.lc4605.to_csv("LC4605.csv")

    # LC4201EW  Tenure by ethnic group by age - Household Reference Persons
    # "C_AGE": {
    #   "0": "All categories: Age",
    #   "1": "Age 24 and under",
    #   "2": "Age 25 to 49",
    #   "3": "Age 50 to 64",
    #   "4": "Age 65 and over"
    # },
    table = "NM_879_1"
    query_params = common_params.copy()
    query_params["C_TENHUK11"] = "2,3,5,6"
    query_params["C_AGE"] = "1...4"
    query_params["C_ETHPUK11"] = "2...8"
    query_params["select"] = "GEOGRAPHY_CODE,C_AGE,C_ETHPUK11,C_TENHUK11,OBS_VALUE"
    self.lc4201 = self.api.get_data("LC4201EW", table, query_params)

    # QS111EW - Household lifestage
    # Stages correspond to:
    # LIFESTAGE   LC4201  LC1102
    # <35          1,2*     1,2
    # 35-54        2*,3*    3,4*
    # 55-64        3*       4*
    # >=65         4        5
    # * overlaps two categories
    table = "NM_511_1"
    query_params = common_params.copy()
    query_params["C_HHLSHUK11"] = "2,3,4,6,7,8,10,11,12,14,15,16"
    query_params["RURAL_URBAN"] = "0"
    query_params["select"] = "GEOGRAPHY_CODE,C_HHLSHUK11,OBS_VALUE"
    self.qs111 = self.api.get_data("QS111EW", table, query_params)

    # LC1102EW - Living arrangements by age - Household Reference Persons
    # NOTE DIFFERENT AGE CATEGORIES
    #   "0": "All categories: Age",
    #   "1": "Age 24 and under",
    #   "2": "Age 25 to 34",
    #   "3": "Age 35 to 49",
    #   "4": "Age 50 to 64",
    #   "5": "Age 65 and over"
    # },
    table = "NM_871_1"
    query_params = common_params.copy()
    query_params["C_AGE"] = "1...5"
    query_params["C_LARPUK11"] = "2,3,5,6,7,8,9"
    query_params["select"] = "GEOGRAPHY_CODE,C_AGE,C_LARPUK11,OBS_VALUE"
    self.lc1102 = self.api.get_data("LC1102EW", table, query_params)

    # LC6115 HRP: composition by NSSEC?

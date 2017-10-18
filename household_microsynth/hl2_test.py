import humanleague as hl
import ukcensusapi.Nomisweb as Api
import numpy as np
from pandas import MultiIndex

def unmap(values, mapping):
  """
  Converts values (census category enumerations)
  """
  i = 0
  for m in mapping:
    values.replace(to_replace=m, value=i, inplace=True)
    i += 1

def remap(values, mapping):
  i = 0
  for m in mapping:
    values.replace(to_replace=m, value=i, inplace=True)
    i += 1

def unlistify(table, columns, sizes, values):
  pivot = table.pivot_table(columns=columns, values=values)
  # order must be same as column order above
  a = np.zeros(sizes, dtype=int)
  a[pivot.index.labels] = pivot.values.flat
  return a  

api = Api.Nomisweb("./cache")

resolution = api.GeoCodeLookup["OA11"]

lad_codes = api.get_lad_codes("Newcastle upon Tyne")

area_codes = api.get_geo_codes(lad_codes, resolution)
print(area_codes)

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

area_map = lc4404.GEOGRAPHY_CODE.unique()
rooms_map = [1,2,3,4,5,6]
tenure_map = [2,3,5,6]
occupants_map = [1,2,3,4]
bedrooms_map = [1,2,3,4]

# construct seed disallowing states where B>R]
#            T  R  S  B
s = np.ones([4, 6, 4, 4])
# set  = 0
for r in range(0,6):
  for b in range(r+1,4):
    s[:,r,:,b] = 0

print (len(area_map))
for area in area_map:
  tenure_rooms_occ = lc4404.loc[lc4404.GEOGRAPHY_CODE == area].copy()
  # unmap indices
# TODO might be quicker to unmap the entire table upfront
  unmap(tenure_rooms_occ.C_TENHUK11, tenure_map)
  unmap(tenure_rooms_occ.C_ROOMS, rooms_map)
  unmap(tenure_rooms_occ.C_SIZHUK11, occupants_map)

  m4404 = unlistify(tenure_rooms_occ, 
                    ["C_TENHUK11","C_ROOMS","C_SIZHUK11"], 
                    [len(tenure_map),len(rooms_map),len(occupants_map)], 
                    "OBS_VALUE")

  tenure_beds_occ = lc4405.loc[lc4405.GEOGRAPHY_CODE == area].copy()

  # unmap indices
  unmap(tenure_beds_occ.C_BEDROOMS, rooms_map)
  unmap(tenure_beds_occ.C_TENHUK11, tenure_map)
  unmap(tenure_beds_occ.C_SIZHUK11, occupants_map)

  m4405 = unlistify(tenure_beds_occ,
                    ["C_TENHUK11","C_BEDROOMS","C_SIZHUK11"],
                    [len(tenure_map),len(bedrooms_map),len(occupants_map)],
                    "OBS_VALUE")

  # p = hl.qis([np.array([0,1,2]), np.array([0,3,2])], [m4404, m4405])
  # if isinstance(p, str):
  #   print(area + " QIS: " + p)
  # else:
  #   print(area + " QIS: " + str(p["conv"]))

  # print(m4404)
  # print(m4405)
  # print(s)
  # print(np.sum(m4404))

  # p = hl.ipf(s, [np.array([0,1,2]), np.array([0,3,2])], [m4404.astype(float), m4405.astype(float)])
  # print(area + " IPF: " + str(p["conv"]))

  # TODO relax IPF tolerance and maxiters when used within QISI
  p = hl.qisi(s, [np.array([0,1,2]), np.array([0,3,2])], [m4404, m4405])
  print(area + " QIS-I: " + str(p["conv"]))
  # if isinstance(p, str):
  #   print(area + " QIS-I: " + p)
  # elif not p["conv"]:
  #   print(area + " QIS-I: did not converge")


# tenure_rooms_occ = lc4404.copy()
# # unmap indices
# # TODO might be quicker to unmap the entire table upfront
# unmap(tenure_rooms_occ.GEOGRAPHY_CODE, area_map)
# unmap(tenure_rooms_occ.C_TENHUK11, tenure_map)
# unmap(tenure_rooms_occ.C_ROOMS, rooms_map)
# unmap(tenure_rooms_occ.C_SIZHUK11, occupants_map)

# m4404 = unlistify(tenure_rooms_occ, 
#                   ["GEOGRAPHY_CODE", "C_TENHUK11", "C_ROOMS", "C_SIZHUK11"], 
#                   [len(area_map), len(tenure_map), len(rooms_map), len(occupants_map)], 
#                   "OBS_VALUE")

# tenure_beds_occ = lc4405.copy()
# # unmap indices
# # TODO might be quicker to unmap the entire table upfront
# unmap(tenure_beds_occ.GEOGRAPHY_CODE, area_map)
# unmap(tenure_beds_occ.C_TENHUK11, tenure_map)
# unmap(tenure_beds_occ.C_BEDROOMS, bedrooms_map)
# unmap(tenure_beds_occ.C_SIZHUK11, occupants_map)

# m4405 = unlistify(tenure_beds_occ, 
#                   ["GEOGRAPHY_CODE", "C_TENHUK11", "C_BEDROOMS", "C_SIZHUK11"], 
#                   [len(area_map), len(tenure_map), len(bedrooms_map), len(occupants_map)], 
#                   "OBS_VALUE")

# p = hl.qis([np.array([0,1,2,3]), np.array([0,1,4,3])], [m4404, m4405])
# print(area + " QIS: " + str(p["conv"]))
# # construct seed disallowing states where B>R]
# #            T  R  S  B
# s = np.ones([len(area_map), 4, 6, 4, 4])
# # set  = 0
# for r in range(0,6):
#   for b in range(r+1,4):
#     s[:,:,r,:,b] = 0

# print(m4404)
# print(m4405)
# print(s)
# print(np.sum(m4404))

# p = hl.ipf(s, [np.array([0,1,2]), np.array([0,3,2])], [m4404.astype(float), m4405.astype(float)])
# print(area + " IPF: " + str(p["conv"]))

# p = hl.qisi(s, [np.array([0,1,2]), np.array([0,3,2])], [m4404, m4405])
# print(area + " QIS-I: " + str(p["conv"]))
# if isinstance(p, str):
#   print(area + " QIS-I: " + p)
# elif not p["conv"]:
#   print(area + " QIS-I: did not converge")

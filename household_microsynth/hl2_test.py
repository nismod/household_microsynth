import humanleague as hl
import ukcensusapi.Nomisweb as Api
import numpy as np
from pandas import MultiIndex

def unmap(values, mapping):
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

area_codes = api.get_lad_codes("Newcastle upon Tyne")

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

lc4404=lc4404.loc[lc4404.GEOGRAPHY_CODE=="E08000021"]
# unmap indices
rooms_map = [1,2,3,4,5,6]
tenure_map = [2,3,5,6]
occupants_map = [1,2,3,4]
unmap(lc4404.C_ROOMS, rooms_map)
unmap(lc4404.C_TENHUK11, tenure_map)
unmap(lc4404.C_SIZHUK11, occupants_map)
#print(lc4404)
print(lc4404.C_TENHUK11.unique())
m4404 = unlistify(lc4404, ["C_TENHUK11","C_ROOMS","C_SIZHUK11"], 
                          [len(tenure_map),len(rooms_map),len(occupants_map)], "OBS_VALUE")

print(m4404)

# LC4405EW - Tenure by household size by number of bedrooms
table = "NM_890_1"
query_params = common_params.copy()
query_params["C_TENHUK11"] = "2,3,5,6"
query_params["C_BEDROOMS"] = "1...4"
query_params["C_SIZHUK11"] = "1...4"
query_params["select"] = "GEOGRAPHY_CODE,C_SIZHUK11,C_TENHUK11,C_BEDROOMS,OBS_VALUE"
lc4405 = api.get_data("LC4405EW", table, query_params)

lc4405=lc4405.loc[lc4405.GEOGRAPHY_CODE=="E08000021"]


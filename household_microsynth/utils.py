# utility functions

import numpy as np
import pandas as pd

# TODO make private static nonmember...
def people_per_bedroom(people, bedrooms):
  ppbed = people / bedrooms
  if ppbed <= 0.5:
    return 1 # (0,0.5]
  if ppbed <= 1:
    return 2 # (0.5, 1]
  if ppbed <= 1.5:
    return 3 # (1, 1.5]
  return 4 # >1.5

def check(msynth, total_occ_dwellings, total_households, total_communal):
  # correct number of dwellings
  assert len(msynth.dwellings) == msynth.total_dwellings
  # no missing/NaN values
  assert not pd.isnull(msynth.dwellings).values.any()

  # category values are within those expected
  assert np.array_equal(sorted(msynth.dwellings.BuildType.unique()), msynth.type_index)
  #assert np.array_equal(sorted(dwellings.Tenure.unique()), tenure_index) communal residence type gets added
  #print(sorted(dwellings.Tenure.unique()))
  assert np.array_equal(sorted(msynth.dwellings.Composition.unique()), msynth.comp_index)
  assert np.array_equal(sorted(msynth.dwellings.PPerBed.unique()), msynth.ppb_index)
  assert np.array_equal(sorted(msynth.dwellings.CentralHeating.unique()), msynth.ch_index)

  # occupied/unoccupied totals correct
  assert len(msynth.dwellings[(msynth.dwellings.Composition != 6) & (msynth.dwellings.BuildType != 6)]) == total_occ_dwellings
  assert len(msynth.dwellings[msynth.dwellings.Composition == 6]) == total_households - total_occ_dwellings

  # household/communal totals correct
  assert len(msynth.dwellings[msynth.dwellings.BuildType != 6]) == total_households
  assert len(msynth.dwellings[msynth.dwellings.BuildType == 6]) == total_communal

  # BuildType
  print("BuildType: Syn v Agg")
  for i in msynth.type_index:
    if i != 6:
      assert len(msynth.dwellings[(msynth.dwellings.BuildType == i) 
                               & (msynth.dwellings.Composition != 6)]) == sum(msynth.lc4402[msynth.lc4402.C_TYPACCOM == i].OBS_VALUE)
    else:
      assert len(msynth.dwellings[(msynth.dwellings.BuildType == i)
                               & (msynth.dwellings.Composition != 6)]) == sum(msynth.communal.OBS_VALUE)

  # Tenure
  for i in msynth.tenure_index:
    assert len(msynth.dwellings[(msynth.dwellings.Tenure == i)
                              & (msynth.dwellings.Composition != 6)]) == sum(msynth.lc4402[msynth.lc4402.C_TENHUK11 == i].OBS_VALUE)

  # central heating (ignoring unoccupied)
  print("CentHeat: Syn v Agg")
  for i in msynth.ch_index:
    assert len(msynth.dwellings[(msynth.dwellings.CentralHeating == i)
                             & (msynth.dwellings.Composition != 6)
                             & (msynth.dwellings.BuildType != 6)]) == sum(msynth.lc4402[msynth.lc4402.C_CENHEATHUK11 == i].OBS_VALUE)

  # composition
  print("Comp: Syn v Agg")
  for i in msynth.comp_index:
    if i != 6:
      assert len(msynth.dwellings[(msynth.dwellings.Composition == i)
                               & (msynth.dwellings.BuildType != 6)]) == sum(msynth.lc4408[msynth.lc4408.C_AHTHUK11 == i].OBS_VALUE)
    else:
      assert len(msynth.dwellings[(msynth.dwellings.Composition == i)
                               & (msynth.dwellings.BuildType != 6)]) == sum(msynth.ks401[msynth.ks401.CELL == 6].OBS_VALUE)

  # Rooms (ignoring communal and unoccupied)
  assert np.array_equal(sorted(msynth.dwellings[msynth.dwellings.BuildType != 6].Rooms.unique()), msynth.lc4404["C_ROOMS"].unique())
  print("Rooms: Syn v Agg")
  for i in msynth.lc4404["C_ROOMS"].unique():
    assert len(msynth.dwellings[(msynth.dwellings.Rooms == i)
                             & (msynth.dwellings.Composition != 6)
                             & (msynth.dwellings.BuildType != 6)]) == sum(msynth.lc4404[msynth.lc4404.C_ROOMS == i].OBS_VALUE)
  print("Zero rooms: ", len(msynth.dwellings[msynth.dwellings.Rooms == 0]))

  # Bedrooms (ignoring communal and unoccupied)
  assert np.array_equal(sorted(msynth.dwellings[msynth.dwellings.BuildType != 6].Bedrooms.unique()), msynth.lc4405["C_BEDROOMS"].unique())
  print("Bedrooms: Syn v Agg")
  for i in msynth.lc4405["C_BEDROOMS"].unique():
    assert(len(msynth.dwellings[(msynth.dwellings.Bedrooms == i)
                             & (msynth.dwellings.Composition != 6)
                             & (msynth.dwellings.BuildType != 6)]) == sum(msynth.lc4405[msynth.lc4405.C_BEDROOMS == i].OBS_VALUE))
  print("Zero bedrooms: ", len(msynth.dwellings[msynth.dwellings.Bedrooms == 0]))
  print("OK")


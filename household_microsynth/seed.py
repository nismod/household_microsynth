""" 
seed.py 
Functionality for generating seed data for the microsynthesis

"""
import numpy as np
import pandas as pd


# T: tenure
# R: rooms
# O: occupants
# B: bedrooms
# H: household composition
# wave 3 is census year (2011)
def get_survey_TROBH(waveno=3):
  filename = "../../UKsurvey/data/crosstab_wave" + str(waveno) + ".csv"
  xtab = pd.read_csv(filename)
  xtab.rename({"size": "occupants", "count": "frequency"}, axis=1, inplace=True)
  # reorder cols
  cols = ['tenure', 'rooms', 'occupants', 'bedrooms', 'hhtype', 'frequency']
  xtab = xtab[cols]

  shape = [4, 6, 4, 4, 5]

  pivot = xtab.pivot_table(index=cols[:-1], values="frequency")
  # order must be same as column order above
  a = np.zeros(shape, dtype=float)
  a[tuple(pivot.index.labels)] = pivot.values.flat

  # add small probability of being in an unobserved state but ensure impossible states stay impossible
  # should probably be 0.5 rather than 0.5/np.sum(a)... 
  a = (a + 0.5 / np.sum(a)) * get_impossible_TROBH()
  return a

def get_impossible_TROBH():
  """ zeros out impossible (beds>rooms, single household with >1 occupants) states, all others are equally probable """
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
  return constraints

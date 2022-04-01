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
  # ensure array
  if isinstance(waveno, int):
    waveno=[waveno]
  
  cols = ['tenure', 'rooms', 'occupants', 'bedrooms', 'hhtype']
  shape = [4,        6,       4,           4,          5]
  seed = np.zeros(shape, dtype=float)
  for w in waveno:
    filename = "./persistent_data/crosstab_wave" + str(w) + ".csv"
    xtab = pd.read_csv(filename)

    pivot = xtab.pivot_table(index=cols, values="frequency")
    # order must be same as column order above
    a = np.zeros(shape, dtype=float)
    for i, idx in enumerate(pivot.index):
      a[idx] = pivot.values.flat[i]
    seed = seed + a

  # add small probability of being in an unobserved state but ensure impossible states stay impossible
  # 0.5 representing approximately the probability threshhold of the state not being seen in the survey
  seed = (seed + 0.5) * get_impossible_TROBH()
  return seed

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


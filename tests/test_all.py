from unittest import TestCase

import household_microsynth.microsynthesis as hhms
import ukcensusapi.Nomisweb as Api

class Test(TestCase):
  api = Api.Nomisweb("./")
  #query = Census.Query(api)

  # just to ensure test harness works
  def test_init(self):
    self.assertTrue(True)

  def test_getCensusData(self):
    region = "City of London"
    resolution = Api.Nomisweb.MSOA
    nDwellings = 5530
    nOccDwellings = 4385
    nPeople = 7375

    (LC4402, LC4404, LC4405, LC4408, LC1105EW, KS401EW) = hhms.getCensusData(region, resolution)
    # check geography is correct
    self.assertTrue(LC4402.GEOGRAPHY_CODE.unique() == ['E02000001'])
    # check totals are correct
    self.assertTrue(LC4402.OBS_VALUE.sum() == nOccDwellings)    
    self.assertTrue(LC4404.OBS_VALUE.sum() == nOccDwellings)    
    self.assertTrue(LC4405.OBS_VALUE.sum() == nOccDwellings)    
    self.assertTrue(LC4408.OBS_VALUE.sum() == nOccDwellings) 
    self.assertTrue(LC1105EW.OBS_VALUE.sum() == nPeople)    
    self.assertTrue(KS401EW.OBS_VALUE.sum() == nDwellings)

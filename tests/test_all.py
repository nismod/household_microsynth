from unittest import TestCase

#import ukcensusapi.Nomisweb as Api
import household_microsynth.Microsynthesis as Households

class Test(TestCase):
  cache = "./cache"
  microsynth = Households.Microsynthesis(cache)
  #query = Census.Query(api)

  # just to ensure test harness works
  def test_init(self):
    self.assertTrue(True)

  def test_get_census_data(self):
    region = "City of London"
    resolution = self.microsynth.api.MSOA # "MSOA" 
    nDwellings = 5530
    nOccDwellings = 4385
    nPeople = 7375
   
    self.microsynth.get_census_data(region, resolution)
    # check geography is correct
    self.assertTrue(self.microsynth.lc4402.GEOGRAPHY_CODE.unique() == ['E02000001'])
    # check totals are correct
    self.assertTrue(self.microsynth.lc4402.OBS_VALUE.sum() == nOccDwellings)    
    self.assertTrue(self.microsynth.lc4404.OBS_VALUE.sum() == nOccDwellings)    
    self.assertTrue(self.microsynth.lc4405.OBS_VALUE.sum() == nOccDwellings)    
    self.assertTrue(self.microsynth.lc4408.OBS_VALUE.sum() == nOccDwellings) 
    self.assertTrue(self.microsynth.lc1105.OBS_VALUE.sum() == nPeople)    
    self.assertTrue(self.microsynth.ks401.OBS_VALUE.sum() == nDwellings)

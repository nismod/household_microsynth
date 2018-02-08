from unittest import TestCase

#import ukcensusapi.Nomisweb as Api
import household_microsynth.household as hh_msynth
import household_microsynth.ref_person as hrp_msynth
import household_microsynth.utils as Utils

class Test(TestCase):

  # City of London MSOA (one geog area)
  def test_hh1(self):
    region = "E09000001"
    resolution = "MSOA11"
    cache = "./cache"
    microsynth = hh_msynth.Household(region, resolution, cache)
    num_dwellings = 5530
    num_occ_dwellings = 4385
    num_communal = 42
    pop_communal = 188
    pop_occupied = 7073

    # any problems and assert will fail
    microsynth.run()

    self.assertTrue(Utils.check_hh(microsynth, num_occ_dwellings, num_dwellings, num_communal, pop_occupied, pop_communal))

  def test_hrp1(self):
    region = "E09000001"
    resolution = "MSOA11"
    cache = "./cache"
    microsynth = hrp_msynth.ReferencePerson(region, resolution, cache)
    num_occ_dwellings = 4385
    
    # any problems and assert will fail
    microsynth.run()

    self.assertTrue(Utils.check_hrp(microsynth, num_occ_dwellings))

  # TODO more tests

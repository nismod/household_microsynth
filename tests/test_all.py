from unittest import TestCase

#import ukcensusapi.Nomisweb as Api
import household_microsynth.microsynthesis as Households
import household_microsynth.utils as Utils

class Test(TestCase):

  # City of London MSOA (one geog area)
  def test1(self):
    region = "City of London"
    resolution = "MSOA11"
    cache = "./cache"
    microsynth = Households.Microsynthesis(region, resolution, cache)
    num_dwellings = 5530
    num_occ_dwellings = 4385
    num_communal = 42
    pop_communal = 188
    pop_occupied = 7073

    # any problems and assert will fail
    microsynth.run()

    self.assertTrue(Utils.check(microsynth, num_occ_dwellings, num_dwellings, num_communal, pop_occupied, pop_communal))

  # TODO more tests?

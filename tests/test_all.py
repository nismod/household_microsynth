from unittest import TestCase

#import ukcensusapi.Nomisweb as Api
import household_microsynth.microsynthesis as Households

class Test(TestCase):

  # City of London MSOA (one geog area)
  def test1(self):
    region = "City of London"
    resolution = "MSOA" 
    cache = "./cache"
    microsynth = Households.Microsynthesis(region, resolution, cache)
    nDwellings = 5530
    nOccDwellings = 4385
    nPeople = 7375

    # any problems and assert will fail
    microsynth.run()

  # TODO more tests?


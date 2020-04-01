from unittest import TestCase

# import ukcensusapi.Nomisweb as Api
import household_microsynth.household as hh_msynth
import household_microsynth.ref_person as hrp_msynth
import household_microsynth.utils as Utils
from household_microsynth.output_endpoint import Output
import os
import pandas as pd


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
        pop_occupied_lb = 7073

        # any problems and assert will fail
        microsynth.run()

        self.assertTrue(
            Utils.check_hh(microsynth, num_occ_dwellings, num_dwellings, num_communal, pop_occupied_lb, pop_communal))

    # City of London MSOA (one geog area)
    def test_sc1(self):
        region = "S12000023"  # Orkney is least populated council area
        resolution = "OA11"
        cache = "./cache"
        microsynth = hh_msynth.Household(region, resolution, cache)
        num_dwellings = 10357
        num_occ_dwellings = 9725
        num_communal = 69
        pop_communal = 198
        pop_occupied_lb = 20506

        # any problems and assert will fail
        microsynth.run()

        self.assertTrue(
            Utils.check_hh(microsynth, num_occ_dwellings, num_dwellings, num_communal, pop_occupied_lb, pop_communal,
                           scotland=True))

    # This can be used to test a custom output function that overrides the default logic.
    def test_custom_endpoint(self):
        Output.OUTPUT_DIR = "./tests/data/"
        df = pd.read_csv("tests/persistent_data/hh_sample_output.csv")
        df.name = "hh_sample_output.csv"
        Output.send(pandas_df=df)

    def test_hh_default_endpoint(self):
        Output.OUTPUT_DIR = "tests/data/"
        df = pd.read_csv("tests/persistent_data/hh_sample_output.csv")
        df.name = "hh_sample_output.csv"
        Output.send(pandas_df=df)
        self.assertTrue(os.path.isfile("tests/data/hh_sample_output.csv"))

    def test_hrp1(self):
        region = "E09000001"
        resolution = "MSOA11"
        cache = "./cache"
        microsynth = hrp_msynth.ReferencePerson(region, resolution, cache)
        num_occ_dwellings = 4385

        # any problems and assert will fail
        microsynth.run()

        self.assertTrue(Utils.check_hrp(microsynth, num_occ_dwellings))

    def test_hrp_default_endpoint(self):
        Output.OUTPUT_DIR = "tests/data/"
        df = pd.read_csv("tests/persistent_data/hrp_sample_output.csv")
        df.name = "hrp_sample_output.csv"
        Output.send(pandas_df=df)
        self.assertTrue(os.path.isfile("tests/data/hrp_sample_output.csv"))

    def tearDown(self):
        if os.path.exists("tests/data/hh_sample_output.csv"):
            os.remove("tests/data/hh_sample_output.csv")
        if os.path.exists("tests/data/hrp_sample_output.csv"):
            os.remove("tests/data/hrp_sample_output.csv")

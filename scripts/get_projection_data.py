import sys
from household_microsynth.projection_data import batch_newbuilds


def main(start_year, end_year):
    batch_newbuilds(start_year, end_year)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python3 scripts/get_projection_data.py start_year end_year")
    else:
        start_year = int(sys.argv[1])
        end_year = int(sys.argv[2])
        print("Collating new build data from " + str(start_year) + " to " + str(end_year))
        main(start_year, end_year)

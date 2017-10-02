
# Household projection

import datetime
from urllib import request
#from urllib.error import HTTPError
#from urllib.error import URLError
#from urllib.parse import urlencode
#from socket import timeout
import pandas as pd
import io
#import csv


def get_postcode_lookup(filename):
  return pd.read_csv(filename, sep=";")

# Example URL for downloading new build sales
# http://landregistry.data.gov.uk/app/ppd/ppd_data.csv?et%5B%5D=lrcommon%3Afreehold&et%5B%5D=lrcommon%3Aleasehold&header=true&limit=all&max_date=31+July+2016&min_date=1+July+2016&nb%5B%5D=true&ptype%5B%5D=lrcommon%3Adetached&ptype%5B%5D=lrcommon%3Asemi-detached&ptype%5B%5D=lrcommon%3Aterraced&ptype%5B%5D=lrcommon%3Aflat-maisonette&tc%5B%5D=ppd%3AstandardPricePaidTransaction&tc%5B%5D=ppd%3AadditionalPricePaidTransaction
def get_newbuilds(start_date, end_date):

  url = "http://landregistry.data.gov.uk/app/ppd/ppd_data.csv?et%5B%5D=lrcommon%3Afreehold&et%5B%5D=lrcommon%3Aleasehold&header=true&limit=all&max_date=" \
      + end_date.strftime("%d+%B+%Y") + "&min_date=" + start_date.strftime("%d+%B+%Y") \
      + "&nb%5B%5D=true&ptype%5B%5D=lrcommon%3Adetached&ptype%5B%5D=lrcommon%3Asemi-detached&ptype%5B%5D=lrcommon%3Aterraced" \
      + "&ptype%5B%5D=lrcommon%3Aflat-maisonette&tc%5B%5D=ppd%3AstandardPricePaidTransaction&tc%5B%5D=ppd%3AadditionalPricePaidTransaction"

  print(start_date.strftime("%d+%B+%Y") + " to " + end_date.strftime("%d+%B+%Y"))

  response = request.urlopen(url)

  newbuild_data = pd.read_csv(io.StringIO(response.read().decode('utf-8')))

  return newbuild_data

if __name__ == "__main__":

  pcdb = get_postcode_lookup("~/postcode_lookup_20170921.csv.gz")

  print(pcdb.columns.values)

  start_date = datetime.date(2016,7,1)
  # add 1y, subtract 1d
  end_date = datetime.date(2016,7,7)

  # newbuilds = get_newbuilds(start_date, end_date)
  # newbuilds.to_csv("~/newbuilds_test.csv")
  newbuilds = pd.read_csv("~/newbuilds_test.csv")
  print(newbuilds.head())

  print(len(newbuilds.index))
  for i in range(0, len(newbuilds.index)):
    postcode = newbuilds.at[i,"postcode"]
    print(len(pcdb.loc[pcdb.Postcode1 == postcode]))

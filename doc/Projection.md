# Notes: Household projection

## Methodology

Determine instances of new household formation within a time frame using the following data:
- land registry newbuild data by postcode
- mapping of postcodes to geographical area (LSOA and above)

The latter must be up-to-date since new builds often generate new postcodes.

Produce a dataset from this containing:
- timeframe (in filename)
- LSOA
- count of new properties by build type* (Detached/Semi/Terrace/Flat)
- (TBC) tenure

*Uses census category codes: (Detached:2, Semi:3, Terrace:4, Flat:5). Other types (parking spaces, etc) are not queried

where postcodes are not found in the lookup, LSOA is set to UNKNOWN
a small number of entries in the land registry data do not have postcodes, again LSOA is set to UNKNOWN

### Data Sources

[HM Land Registry Open Data - Price Paid Data](http://landregistry.data.gov.uk/app/ppd/)

[National Statistics Postcode Lookup UK](https://data.gov.uk/dataset/national-statistics-postcode-lookup-uk)

The dataset is >700MB so has been postprocessed to remove unnecessary fields.

See also:
[Split postcodes by OA](https://www.nomisweb.co.uk/census/2011/postcode_headcounts_and_household_estimates)
Sadly this only lists postcodes that are split between OAs, and is not up-to-date.

## Issues

- postcode to OA lookup would be better - could not find such data on ONS website.
- 
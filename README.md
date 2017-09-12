# Household Microsynthesis

A python package for microsynthesising household poulations from census data, including communal and unoccupied residences.

## Installation

### Dependencies

- `python3`

The following are specified in `requirements.txt` and should be automatically installed, manual steps are shown below just in case. 

- [UKCensusAPI](https://github.com/virgesmith/UKCensusAPI)
```
pip3 install git+git://github.com/virgesmith/UKCensusAPI.git
```
- [humanleague](https://github.com/virgesmith/humanleague)
```
pip3 install git+git://github.com/virgesmith/humanleague.git@1.0.1
```
NB Ensure you install the version 1.0.1 of humanleague. Later versions have breaking changes and/or are under heavy development.

### Installation and Testing
```
./setup.py install
./setup.py test
```

### Running
```
scripts/run_microsynth.py <region(s)> <resolution>
```
where region can be a one or more local authorities (or one of England, EnglandWales, GB, UK) and resolution can be one of: LA, MSOA, LSOA, OA. If there are spaces in the former, enclose the argument in quotes, e.g.
```
scripts/run_microsynth.py "City of London" OA
```
# Introduction

This document outlines the methodology and software implementation of a scalable small area microsynthesis of dwellings in a given region. It uses a microsynthesis technique developed by the author (publication in press) that uses quasirandom sampling to directly generate non-fractional populations very efficently.

This also introduces and tests (successfully) a newly-developed extension to the microsynthesis technique that can deal with extra constraints (in this case the fact that a household cannot have more bedrooms than rooms).

# Overview

The microsynthesis combines census data on occupied households, communal residences, and unoccupied dwellings to generate a synthetic population of dwellings classified in a number of categories.

It can be used to generate a realistic synthetic population of dwellings in a region at a specified geopgraphical resolution. Regions can be one or more local authorities or countrywide, and the geographical resolutions supported are: local authority, MSOA, LSOA or OA. The synthetic population is consistent with the census aggregates within the specified geographical resolution.

The term 'unoccupied' in this context means a dwelling that is not permanently occupied, or is unoccupied, _on the census date_. This of course does not mean that the property is permanently unoccupied, and could actually mean that the occupants did not return the census form. It does mean that there is essentially no data available for these properties, other than their existence.

|Category      |Column Name             |Description
|--------------|------------------------|-----------
|Geography     |Area                    |ONS code for geographical area (e.g. E00000001)  
|Build Type    |LC4402_C_TYPACCOM       |Type of dwelling e.g. semi-detached
|Communal Type |QS420EW_CELL            |Type of communal residence, e.g. nursing home
|Tenure        |LC4402_C_TENHUK11       |Ownership, e.g. mortgaged
|Composition   |LC4408_C_AHTHUK11       |Domestic situation, e.g. cohabiting couple
|Occupants     |LC4404EW_C_SIZHUK11     |Number of occupants (capped at 4)
|Rooms         |LC4404EW_C_ROOMS        |Number of rooms (capped at 6)
|Bedrooms      |LC4405EW_C_BEDROOMS     |Number of bedrooms (capped at 4)
|PPerBed       |LC4408EW_C_PPBROOMHEW11 |Ratio of occupants to bedrooms (approximate) 
|CentHeat      |LC4402_C_CENHEATHUK11   |Presence of central heating 
|EconStatus    |LC4601EW_C_ECOPUK11     |Economic status of household reference person, e.g employed full-time
|Ethnicity     |LC4202EW_C_ETHHUK11     |Ethnicity of household reference person, e.g. Asian
|NumCars       |LC4202EW_C_CARSNO       |Number of cars used by household (capped at 2)

Since occupants, rooms and bedrooms are capped (with the final value representing an '...or more' category, there is some imprecision in the microsynthesis:

- the count of population in households is lower than the true population estimate.}
- the value of persons per bedroom (`PPerBed' above) does not quite match the census data, due to the imprecision inherent in the 4+ categories. This makes it difficult to use it as a link variable between household composition and rooms/bedrooms. (This mismatch could potentially be used to refine estimates of persons and bedrooms in properties, but is out of scope for the moment.)

# Input Data

The only user inputs required to run the model is the geographical area under consideration, e.g. 'Newcastle upon Tyne' and the required geographical resolution, e.g. 'LSOA'. 

Downloading and cacheing of Census data and metadata from nomisweb.co.uk is handled by the UKCensusAPI package. See [https://github.com/virgesmith/UKCensusAPI](UKCensusAPI) for further details. 

__It is important that users ensure they have an account with nomisweb.co.uk and an API key, otherwise data downloads may be truncated which will likely result in inconsistent table populations. The microsynthesis performs checks on the input data and  fail.__

|Table     |Description|
|----------|-----------|
|`LC4402EW`| Accommodation type by type of central heating in household by tenure|  
|`LC4404EW`| Tenure by household size by number of rooms|
|`LC4405EW`| Tenure by household size by number of bedrooms|   
|`LC4408EW`| Tenure by number of persons per bedroom in household by household type|   
|`LC1105EW`| Residence type by sex by age|
|`KS401EW` | Dwellings, household spaces and accommodation type|         
|`QS420EW` | Communal establishment management and type - Communal establishments|         
|`QS421EW` | Communal establishment management and type - People|
|`LC4601EW`| Tenure by economic activity by age - Household Reference Persons |
|`LC4202EW`| Tenure by car or van availability by ethnic group of Household Reference Person (HRP) |

# Methodology

## Overview

The microsynthesis methodology can be split into three distinct parts: occupied households, communal residences, and unoccupied dwellings. The assumptions and data limitations differ for each of these and consequently the approach does too. 

TODO UNKNOWN/NOTAPPLICABLE... the table now explicitly contains UNKNOWN (-1) values (e.g. for ethnicity of unoccupied household) and NOTAPPLICABLE (-2) (e.g. communal residence type for a ‘normal’ household), but should never contain empty values for any category.

## Limitations of the input data

### General
- Data is from the 2011 census and assumed to be accurate at the time, but it is already over 6 years old.

### Occupied Households
- No census table is known that links rooms directly to bedrooms.
- There are small discrepancies in the counts in the LC4601EW (economic status) table, which occasionally has one fewer entry in an area.

### Communal Residences
- The only available data is a count of the number of residences of a particular type within the area, and the total number of people in that type of residence in that area. The occupants are split evenly amongst the appropriate residences.

### Unoccupied Households
- No census data is available that indicate any characteristics of unoccupied dwellings, other than their existence.

## Assumptions

### General


### Occupied Households
All categories are constrained at a minimum by geographical resolution and dwelling tenure, but note also: 

- central heating assignment - no further constraint
- occupants/rooms/bedrooms assignment - bedrooms cannot exceed rooms
- household composition assignment - single occupant households are assigned directly, others are synthesised


### Communal Residences
Census data provides a count of the number of, and total occupants of, each type of communal residence within an an OA. For each communal residence of each type in each OA, an entry is inserted into the overall dwelling population.

Note the assumptions that were made:

- Where there are multiple communal residences of the same type in an OA, the occupants are split equally (rounded to integer) across the residences.
- The tenure of communal residences in not known, not deemed sufficiently important to synthesise. The type of the communal residence is assigned to this field.
- The composition of residences is assigned a single value: `Communal'.
- The type of communal residences is assigned a single value: `Multi-person'.
- All communal residences are assumed to have some form of central heating.

### Unoccupied Households
The microsynthesis is constrained only by OA. Note the assumptions that were made:

- Zero occupants, and thus \(\le0.5\) persons per bedroom, were assigned to each dwelling.
- The type, tenure, rooms, bedrooms and central heating of the dwellings are not given in census data but are deemed sufficiently important to synthesise.
- The composition opf these dwellings is assigned the value `Unoccupied'.
- All communal residences are assumed to have some form of central heating.

The type, tenure, rooms, bedrooms and central heating values for unoccupied dwellings were synthesised by sampling from the (larger) population of occupied households within the OA.

## Consistency

Pre-synthesis checks.

A number of tests are automatically carried out on the synthetic population to ensure that it is consistent with the input data...

# Output Data

The output data consists of a single csv file containing the synthetic population, plus a number of json files containing metadata (one per census table). Each row represents a single dwelling.

For brevity amongst other reasons, only numeric values are stored in the data. Each column name describes a category and a census table from which it came, e.g. column `LC4408_C_AHTHUK11` contains values from the `C_AHTHUK11` category in the `LC4408` table. Inspecting the metadata yields:
```
"C_AHTHUK11": {
  "0": "All categories: Household type",
  "1": "One person household",
  "2": "Married or same-sex civil partnership couple household",
  "3": "Cohabiting couple household",
  "4": "Lone parent household",
  "5": "Multi-person household"
},
```
And thus we know that e.g. the value 5 corresponds to a multi-person household.

## Example

Example output is given in the `example` subdirectory of this repo. The City of London is chosen for its small population and is synthesised at output area (OA) resolution:

```
user@host:~$ scripts/run_microsynthesis.py "City of London" OA
Microsynthesis region:  City of London
Microsynthesis resolution:  OA
Cache directory:  ./cache/
using cached LAD codes: ./cache/lad_codes.json
Writing metadata to  ./cache/LC4402EW_metadata.json
Downloading and cacheing data: ./cache/LC4402EW_b36188dcd2ba0c6b921680d60da39b04.tsv
Writing metadata to  ./cache/LC4404EW_metadata.json
Downloading and cacheing data: ./cache/LC4404EW_11633101d40d0275d7a74a26de0afe4a.tsv
Writing metadata to  ./cache/LC4405EW_metadata.json
Downloading and cacheing data: ./cache/LC4405EW_95eb69c9b70390671892586181599c70.tsv
Writing metadata to  ./cache/LC4408EW_metadata.json
Downloading and cacheing data: ./cache/LC4408EW_298bf03d9d321aad2557a9d183e8f2a2.tsv
Writing metadata to  ./cache/LC1105EW_metadata.json
Downloading and cacheing data: ./cache/LC1105EW_58d9dbe719f42457bbcc27eef7e9b997.tsv
Writing metadata to  ./cache/KS401EW_metadata.json
Downloading and cacheing data: ./cache/KS401EW_26cd440a079571f0eec02b0a761e6c99.tsv
Writing metadata to  ./cache/QS420EW_metadata.json
Downloading and cacheing data: ./cache/QS420EW_42a7d98b44ce0503409213af9330eedd.tsv
Writing metadata to  ./cache/QS421EW_metadata.json
Downloading and cacheing data: ./cache/QS421EW_efdf6f36faf344559649cac96a264880.tsv
Writing metadata to  ./cache/LC4202EW_metadata.json
Downloading and cacheing data: ./cache/LC4202EW_f2a9b899d0d565fe179ce605a59c5e92.tsv
Writing metadata to  ./cache/LC4601EW_metadata.json
Downloading and cacheing data: ./cache/LC4601EW_65674d2abd7ab592e6e2a23e9dcb57b6.tsv
Households:  5530
Occupied households:  4385
Unoccupied dwellings:  1145
Communal residences:  42
Dwellings:  5572
Total dwellings:  5572
Total population:  7375
Population in occupied households:  7187
Population in communal residences:  188
Population lower bound from occupied households:  7073
Occupied household dwellings underestimate:  114
Number of geographical areas:  31
....WARNING: econ mismatch in E00000007 18 17
..................WARNING: econ mismatch in E00000029 61 60
.........Done. Exec time(s):  70.66071200370789
Checking consistency
Zero rooms:  34
Zero bedrooms:  34
OK
Writing synthetic population to ./synHouseholds.csv
DONE
```

The [output file](examples/synHouseholds.csv) looks like this:

| |Area|LC4402_C_TYPACCOM|QS420EW_CELL|LC4402_C_TENHUK11|LC4408_C_AHTHUK11|LC4404EW_C_SIZHUK11|LC4404EW_C_ROOMS|LC4405EW_C_BEDROOMS|LC4408EW_C_PPBROOMHEW11|LC4402_C_CENHEATHUK11|LC4601EW_C_ECOPUK11|LC4202EW_C_ETHHUK11|LC4202EW_C_CARSNO
|-|----|-----------------|------------|-----------------|-----------------|-------------------|----------------|-------------------|-----------------------|---------------------|-------------------|-------------------|-----------------
|0|E00000001|5|-2|2|1|1|2|2|1|2|5|2|1
|1|E00000001|5|-2|2|1|1|3|3|1|2|5|2|1
|2|E00000001|5|-2|2|1|1|4|3|1|2|8|2|2
|3|E00000001|5|-2|2|1|1|5|1|2|2|7|2|2
|4|E00000001|5|-2|2|1|1|5|1|2|2|14|2|1
|5|E00000001|5|-2|2|1|1|5|2|1|2|14|2|1
|6|E00000001|5|-2|2|1|1|5|2|1|2|14|2|1
|7|E00000001|5|-2|2|1|1|5|2|1|2|5|2|2
|8|E00000001|5|-2|2|1|1|5|2|1|1|8|6|2
...

And there are ten metadata files - one for each census table - which can be used to describe the numeric category values:



- [LC4402EW](examples/LC4402EW_metadata.json)
- [LC4404EW](examples/LC4404EW_metadata.json)
- [LC4405EW](examples/LC4405EW_metadata.json)
- [LC4408EW](examples/LC4408EW_metadata.json)
- [LC1105EW](examples/LC1105EW_metadata.json)
- [KS401EW](examples/KS401EW_metadata.json)
- [QS420EW](examples/QS420EW_metadata.json)
- [QS421EW](examples/QS421EW_metadata.json)
- [LC4202EW](examples/LC4202EW_metadata.json)
- [LC4601EW](examples/LC4601EW_metadata.json)

Negative entries refer to either unknown (-1) or non-applicable (-2) values, and do not correspond to any census enumeration.

# Outstanding Issues

- Zero rooms/bedrooms properties.

Feel free to submit issues...


*[this documentation is in the process of being updated to reflect the current codebase...]*

# Household Microsynthesis

A python package for microsynthesising household poulations from census data, including communal and unoccupied residences.

# Introduction

This document outlines the methodology and software implementation of a scalable small area microsynthesis of dwellings in a given region. It uses a microsynthesis technique developed by the author (publication in press) that uses quasirandom sampling to directly generate non-fractional populations very efficently.

This also introduces and tests (successfully) a newly-developed extension to the microsynthesis technique that can deal with extra constraints (in this case the fact that a household cannot have more bedrooms than rooms).

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
pip3 install git+git://github.com/virgesmith/humanleague.git
```
NB Ensure you install humanleague version 2 or higher - this package uses features that are not available in earlier versions.

### Installation and Testing
```
./setup.py install
./setup.py test
```

### Running
```
scripts/run_microsynth.py <region(s)> <resolution>
```
where region can be a one or more local authorities (or one of England, EnglandWales, GB, UK), specified by either name or ONS/GSS code (e.g. E09000001). If there are spaces in the former, enclose the argument in quotes, e.g.
```
scripts/run_microsynth.py "City of London" OA11
```
Resolution can be one of: LA, MSOA11, LSOA11, OA11. 

# Overview

The microsynthesis combines census data on occupied households, communal residences, and unoccupied dwellings to generate a synthetic population of dwellings classified in a number of categories, shown in the table below.

It can be used to generate a realistic synthetic population of dwellings in a region at a specified geographical resolution. Regions can be one or more local authorities or countrywide, and the geographical resolutions supported are: local authority, MSOA, LSOA or OA. The synthetic population is consistent with the census aggregates within the specified geographical resolution.

The term 'unoccupied' in this context means a dwelling that is not permanently occupied, or is unoccupied, _on the census date_. This of course does not mean that the property is permanently unoccupied, and could actually mean that the occupants did not return the census form. The census tells us only that these properties exist.

Category values for a dwelling may be unknown or unapplicable in the synthesised data. This is simply because some columns are specific to a particular dwelling type (e.g. QS420EW_CELL for communal residences) or information is just unavailable (as is often the case for unoccupied dwellings. These values are indicated as negative numbers in the output, where -1 indicates unknown and -2 non-applicable.

|Category      |Table/Column Name       |Description
|--------------|------------------------|-----------
|Geography     |Area                    |ONS code for geographical area (e.g. E00000001)  
|Build Type    |LC4402_C_TYPACCOM       |Type of dwelling e.g. semi-detached
|Communal Type |QS420EW_CELL            |Type of communal residence, e.g. nursing home
|Tenure        |LC4402_C_TENHUK11       |Ownership, e.g. mortgaged
|Composition   |LC4408_C_AHTHUK11       |Domestic situation, e.g. cohabiting couple
|Occupants     |LC4404EW_C_SIZHUK11     |Number of occupants (capped at 4)
|              |CommunalSize            |Number of communal occupants (estimated)
|Rooms         |LC4404EW_C_ROOMS        |Number of rooms (capped at 6)
|Bedrooms      |LC4405EW_C_BEDROOMS     |Number of bedrooms (capped at 4)
|PPerBed       |LC4408EW_C_PPBROOMHEW11 |Ratio of occupants to bedrooms (approximate) 
|CentHeat      |LC4402_C_CENHEATHUK11   |Presence of central heating 
|SE Class      |LC4605EW_C_NSSEC        |Socio-economic classification of household reference person
|Ethnicity     |LC4202EW_C_ETHHUK11     |Ethnicity of household reference person, e.g. Asian
|NumCars       |LC4202EW_C_CARSNO       |Number of cars used by household (capped at 2)

# Input Data

The only user inputs required to run the model is the geographical area under consideration, e.g. 'Newcastle upon Tyne' and the required geographical resolution, e.g. 'LSOA'. Multiple local authrities can be specified using a comma to separate the names.

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
|`LC4605EW`| Tenure by socio-economic classification - Household Reference Persons |
|`LC4202EW`| Tenure by car or van availability by ethnic group of Household Reference Person (HRP) |

# Methodology

## Overview

In essence, the model converts aggregate census data into a synthetic population of individual households that is consistent with census data at the specified resolution. 

The microsynthesis methodology can be split into three distinct parts: occupied households, communal residences, and unoccupied dwellings. The assumptions and data limitations differ for each of these and consequently the approach does too. See below for more detail.

Where the category values for a specific dwelling are not known (e.g. ethnicity of unoccupied household), or are not applicable (e.g. communal residence type for a standard household), negative values are inserted into the output, with -1 indicating __unknown__ and -2 indicating __not applicable__. These values (deliberately) do not correspond to any census enumeration. Additionally, the value zero is used for the number of occupants in unoccupied households (despite the fact that census convention normally uses this value to indicate an aggregate count over all categories).

## Limitations of the input data

### General
- Data is from the 2011 census and assumed to be accurate at the time, but it is already over 6 years old.

### Occupied Households
- No single census table is known that contains both number of rooms and number of bedrooms, so the categories must be microsynthesised with the additional constraint that there cannot be more bedrooms than rooms.
- There are small discrepancies in the counts in the LC4601EW (economic status) table, which we have observed to occasionally have one fewer entry in an area than the other tables. This is dealt with by oversampling.
- Since occupants, rooms and bedrooms are capped (with the final value representing an '...or more' category, there is some imprecision in the microsynthesis:
  - the count of population in households is lower than the true population estimate.
  - the value of persons per bedroom does not quite match the census data, due to the imprecision inherent in the 4+ categories. This makes it difficult to use it as a link variable between household composition and rooms/bedrooms. (This mismatch could potentially be used to refine estimates of persons and bedrooms in properties, but is out of scope for the moment.)

### Communal Residences
- The only available data is a count of the number of residences of a particular type within the area, and the total number of people in that type of residence in that area. Data on the number of occupants in a specific communal residence is only available when there is only one of its type within the area.
- Quite often, the number of occupants for communal residences is given as zero.
- No data is available on the ethnicity or economic status of communal residents.
- No data is available on the number of cars per communal residence.

### Unoccupied Households
- No census data is available that indicate any characteristics of unoccupied dwellings, other than their existence.

## Model Assumptions

### General
...

### Occupied Households
All categories are constrained at a minimum by geographical resolution and dwelling tenure. Given a particular area and tenure, the following categories are assigned randomly to the population, according to the aggregates for that area and tenure.
- build type
- central heating 
- economic status of household reference person
- ethnicity of household reference person
- number of cars per household
- number of occupants
- rooms/bedrooms assignment is additionally contrained on
  - the number of occupants
  - bedrooms cannot exceed rooms
- persons per bedroom (calculated ignoring the "or more" nature of the final value). 
- household composition assignment
  - single occupant households are assigned directly to dwellings with one occupant
  - others are randomly assigned within the same area and tenure

### Communal Residences
- Where there are multiple communal residences of the same type in an area, the occupants are split equally (rounded to integer) across the residences. 
- Occupant counts for communal residences are stored in the "CommunalSize" column since they do not correspond to the metadata that describes the LC4404EW_C_SIZHUK11 column.
- Tenure and build type are __unknown__.
- The number of rooms and the number of bedrooms are __unknown__.
- The composition of residences is multi-person.
- All communal residences are assumed to have central heating.
- The economic status of communal residents is generally unknown, but sometimes can be inferred by the residence type.
- The ethnicity of the communal residence is mixed/multiple.
- No cars is assumed.

### Unoccupied Households
The type, tenure, rooms, bedrooms and central heating of the dwellings are not given in census data but are deemed sufficiently important to microsynthesise. The microsynthesis is constrained only by area. Since no other information is available, characteristics are assigned by sampling a microsynthesised population of households according to build type, tenure and central heating. Other characteristics are assigned as follows:
- zero occupants
- rooms and bedrooms are assigned randomly from a sample of occupied households in the same area with the same build type.
- Composition, economic stats and ethnicity are __unknown__.
- No cars.

## Consistency

Pre-microsynthesis checks are carried out on the input data, ensuring the table population totals are consistent. The most common reason for these checks failing is that the user has not specified an API key, see the installation section above.

A number of tests are automatically carried out on the synthetic population to ensure that it is consistent with the input data:
- synthesised dwelling population matches expected total
- no category values are empty
- the category values are all within the ranges given by the census data (unknown/unapplicable aside)
- occupied, communal and unoccupied totals are expected
- the totals for each value match census data for the following categories
  - build type
  - tenure
  - central heating
  - composition
  - rooms and bedrooms
  - economic status
  - ethnicity
  - number of cars

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
And thus we know that e.g. the value 5 in the LC4408_C_AHTHUK11 column indicates a multi-person household.

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

The [output file](example/synHouseholds.csv) looks like this:

| |Area|LC4402_C_TYPACCOM|QS420EW_CELL|LC4402_C_TENHUK11|LC4408_C_AHTHUK11|CommunalSize|LC4404EW_C_SIZHUK11|LC4404EW_C_ROOMS|LC4405EW_C_BEDROOMS|LC4408EW_C_PPBROOMHEW11|LC4402_C_CENHEATHUK11|LC4601EW_C_ECOPUK11|LC4202EW_C_ETHHUK11|LC4202EW_C_CARSNO
|-|----|-----------------|------------|-----------------|-----------------|-----------------|-------------------|----------------|-------------------|-----------------------|---------------------|-------------------|-------------------|-----------------
0|E00000001|5|-2|2|1|-2|1|2|2|1|2|14|4|2
1|E00000001|5|-2|2|1|-2|1|3|3|1|2|5|2|2
2|E00000001|5|-2|2|1|-2|1|4|3|1|2|5|2|2
3|E00000001|5|-2|2|1|-2|1|5|1|2|2|14|2|2
4|E00000001|5|-2|2|1|-2|1|5|1|2|2|5|2|2
5|E00000001|5|-2|2|1|-2|1|5|2|1|2|5|2|1
6|E00000001|5|-2|2|1|-2|1|5|2|1|2|7|2|2
7|E00000001|5|-2|2|1|-2|1|5|2|1|2|5|2|1
8|E00000001|5|-2|2|1|-2|1|5|2|1|2|5|2|2
...

And there are ten metadata files - one for each census table - which can be used to describe the numeric category values:

- [LC4402EW](example/LC4402EW_metadata.json)
- [LC4404EW](example/LC4404EW_metadata.json)
- [LC4405EW](example/LC4405EW_metadata.json)
- [LC4408EW](example/LC4408EW_metadata.json)
- [LC1105EW](example/LC1105EW_metadata.json)
- [KS401EW](example/KS401EW_metadata.json)
- [QS420EW](example/QS420EW_metadata.json)
- [QS421EW](example/QS421EW_metadata.json)
- [LC4202EW](example/LC4202EW_metadata.json)
- [LC4605EW](example/LC4605EW_metadata.json)

# Contributing

__Feel free to submit issues (or even pull requests) in the normal github way...__



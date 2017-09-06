
__** WORK IN PROGRESS **__

# Household Microsynthesis

## Installation

### Dependencies

- `python3`

- [UKCensusAPI](https://github.com/virgesmith/UKCensusAPI)
```
pip3 install git+git://github.com/virgesmith/UKCensusAPI.git
```
- [humanleague](https://github.com/virgesmith/humanleague)
```
pip3 install git+git://github.com/virgesmith/humanleague.git@1.0.1
```

### Testing
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

This document outlines the methodology and software implementation of a scalable small area microsynthesis of dwellings in a given region. It uses a microsynthesis technique developed by the author (publication in peer review) that uses quasirandom sampling to directly generate non-fractional populations very efficently.

This work also introduces and tests (successfully) a newly-developed extension to the microsynthesis technique that can deal with extra constraints (in this case the fact that a household cannot have more bedrooms than rooms). 

# Terminology

We use the term `unoccupied' in this work to mean a dwelling that is not permanently occupied, or is unoccupied, _on the census date_. This does not mean that the property is permanently unoccupied, but it does mean that there is essentially no data available for these properties. 

|Category    |Values|  
|------------|------|  
|Geography   |(output area)|  
|Tenure      |Owned, Mortgaged/shared, Rented social, Rented private, (Communal category)|
|BuildType   |Detached, Semi, Terrace, Flat/mobile, Communal|
|Occupants   |1, 2, 3, 4+|
|Rooms       |1, 2, 3, 4, 5, 6+|  
|Bedrooms    |1, 2, 3, 4+|
|CentHeat    |1 (no), 2(yes) | 
|PPerBed     |<=0.5, (0.5,1], (1,1.5], >1.5| 
|Composition |Single person, Married/civil partnership, Cohabiting couple, Single parent, Multi person, Unoccupied|
|EconStatus  | ... |
|Ethnicity   | ... |
|NumCars     | None, One, Two or more|

Since occupants, rooms and bedrooms are capped (with the final value representing an `...or more' category, there is some imprecision in the microsynthesis:

- the count of population in households is lower than the true population estimate.}
- the value of persons per bedroom (`PPerBed' above) does not quite match the census data, due to the imprecision inherent in the 4+ categories. This makes it difficult to use it as a link variable between household composition and rooms/bedrooms. (This mismatch could potentially be used to refine estimates of persons and bedrooms in properties, but is out of scope for the moment.)

# Input Data

The only user inputs required to run the model is the geographical area under consideration, e.g. `Newcastle upon Tyne' and the required geographical resolution, e.g. `LSOA'. 

The required 2011 Census tables are automatically downloaded using the [https://github.com/virgesmith/UKCensusAPI](UKCensusAPI) package from nomisweb.co.uk. (End users should ensure they have an account and an API key, otherwise data downloads may be incomplete.)  Since the data is essentially static, downloads are cached for efficiency.

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

Note the following limitations in the input data:

- No census table is known that links rooms directly to bedrooms.
- No census data is available that indicate any characteristics of unoccupied dwellings.
- For communal residencesthe only available data is a count of the number of residences of a particular type within the area, and the total number of people in that type of residence in that area.
- There are small discrepancies in the counts in the LC4601EW table, occasionally showing one fewer entry in an area.

The Methodology section explains how these limitations are dealt with.

# Output Data

Example runtime output:

```
user@host ~ $ scripts/run_microsynth.py "City of London" OA
Microsynthesis region:  City of London
Microsynthesis resolution:  OA
Cache directory:  ./cache/
Cacheing local authority codes
Using cached data: ./cache/LC4402EW_b36188dcd2ba0c6b921680d60da39b04.tsv
Using cached data: ./cache/LC4404EW_11633101d40d0275d7a74a26de0afe4a.tsv
Using cached data: ./cache/LC4405EW_95eb69c9b70390671892586181599c70.tsv
Using cached data: ./cache/LC4408EW_298bf03d9d321aad2557a9d183e8f2a2.tsv
Using cached data: ./cache/LC1105EW_58d9dbe719f42457bbcc27eef7e9b997.tsv
Using cached data: ./cache/KS401EW_26cd440a079571f0eec02b0a761e6c99.tsv
Using cached data: ./cache/QS420EW_42a7d98b44ce0503409213af9330eedd.tsv
Using cached data: ./cache/QS421EW_efdf6f36faf344559649cac96a264880.tsv
Writing metadata to  ./cache/LC4202EW_metadata.json
Downloading and cacheing data: ./cache/LC4202EW_f2a9b899d0d565fe179ce605a59c5e92.tsv
Using cached data: ./cache/LC4601EW_65674d2abd7ab592e6e2a23e9dcb57b6.tsv
Households:  5530
Occupied households:  4385
Unoccupied dwellings:  1145
Communal residences:  42
Dwellings:  5572
Total dwellings:  5572
Population in occupied households:  7187
Population in communal residences:  188
Population lower bound from occupied households:  7073
Occupied household dwellings underestimate:  114
Number of geographical areas:  31
...............................Done. Exec time(s):  14.46349310874939
Checking consistency
OK
Writing synthetic population to ./synHouseholds.csv
DONE
```

The microsynthesed dwelling population is rendered as a `csv` file. Each row in the table represents an individual dwelling. The columns contain the categories described in the previous section.

For ease of use, enumerated categories (e.g Tenure) are represented in both text and numeric format. The numeric value is generally the same value used by the census; the text values are either the census text, abbreviated in some cases. The tables below map numeric to text values for these categories.

Since no tenure information is forthcoming for communal residences, the Tenure and TenureName columns are repurposed to store information about the type of the communal residence (see table below). The Tenure values are offset by 100 to avoid confusion.


|Category | Text | Value |
|---------|------|-------| 
|BuildType          | Detached | 2 
|                   | Semi | 3  
|                   | Terrace  | 4   
|                   | Flat/mobile | 5    
|                   | Communal | 6   
|Tenure             | Owned | 2 
|                   | Mortgaged/shared | 3  
|                   | Rented social  | 5   
|                   | Rented private | 6   
|(Communal)         | Medical and care establishment: NHS | 102   
|                   | Medical and care establishment: Local Authority | 106 
|                   | Medical and care establishment: Registered Social Landlord/Housing Association | 111 
|                   | Medical and care establishment: Other | 114 
|                   | Other establishment: Defence | 122 
|                   | Other establishment: Prison service | 123 
|                   | Other establishment: Approved premises (probation/bail hostel) | 124 
|                   | Other establishment: Detention centres and other detention | 125 
|                   | Other establishment: Education | 126 
|                   | Other establishment: Hotel: guest house; B\|B; youth hostel | 127 
|                   | Other establishment: Hostel or temporary shelter for the homeless | 128 
|                   | Other establishment: Holiday accommodation (for example holiday parks) | 129 
|                   | Other establishment: Other travel or temporary accommodation | 130 
|                   | Other establishment: Religious | 131 
|                   | Other establishment: Staff/worker accommodation only | 132 
|                   | Other establishment: Other | 133 
|                   | Establishment not stated  | 134   
|PPerBed            | <=0.5   | 1 
|                   | (0.5,1] | 2  
|                   | (1,1.5] | 3   
|                   | >1.5    | 4   
|Composition        | Single person | 1 
|                   | Married/civil partnership | 2  
|                   | Cohabiting couple | 3   
|                   | Single parent | 4    
|                   | Multi person | 5    
|                   | Unoccupied | 6   
|Economic Status    | Economically active: In employment: Employee: Part-time | 4
|                   | Economically active: In employment: Employee: Full-time | 5
|                   | Economically active: In employment: Self-employed: Part-time | 7
|                   | Economically active: In employment: Self-employed: Full-time | 8
|                   | Economically active: In employment: Full-time students | 9
|                   | Economically active: Unemployed: Unemployed (excluding full-time students) | 11
|                   | Economically active: Unemployed: Full-time students | 12
|                   | Economically inactive: Retired | 14
|                   | Economically inactive: Student (including full-time students) | 15
|                   | Economically inactive: Looking after home or family | 16
|                   | Economically inactive: Long-term sick or disabled | 17
|                   | Economically inactive: Other | 18
| Ethnicity         | White: English/Welsh/Scottish/Northern Irish/British | 2
|                   | White: Irish | 3
|                   | White: Other White | 4
|                   | Mixed/multiple ethnic group | 5
|                   | Asian/Asian British | 6
|                   | Black/African/Caribbean/Black British | 7
|                   | Other ethnic group | 8
| NumCars           | No cars in household | 1
|                   | One car in household | 2
|                   | Two or more cars in household | 3

# Microsynthesis methodology

The microsynthesis methodology can be split into three distinct parts:

## Microsynthesis of Occupied Dwellings

All categories are constrained at a minimum by geographical resolution and dwelling tenure, but note also: 

- central heating assignment - no further constraint
- occupants/rooms/bedrooms assignment - bedrooms cannot exceed rooms
- household composition assignment - single occupant households are assigned directly, others are synthesised

## Addition of Communal Residences

Census data provides a count of the number of, and total occupants of, each type of communal residence within an an OA. For each communal residence of each type in each OA, an entry is inserted into the overall dwelling population.

Note the assumptions that were made:

- Where there are multiple communal residences of the same type in an OA, the occupants are split equally (rounded to integer) across the residences.
- The tenure of communal residences in not known, not deemed sufficiently important to synthesise. The type of the communal residence is assigned to this field.
- The composition of residences is assigned a single value: `Communal'.
- The type of communal residences is assigned a single value: `Multi-person'.
- All communal residences are assumed to have some form of central heating.

## Microsynthesis of Unoccupied Dwellings

The microsynthesis is constrained only by OA. Note the assumptions that were made:

- Zero occupants, and thus \(\le0.5\) persons per bedroom, were assigned to each dwelling.
- The type, tenure, rooms, bedrooms and central heating of the dwellings are not given in census data but are deemed sufficiently important to synthesise.
- The composition opf these dwellings is assigned the value `Unoccupied'.
- All communal residences are assumed to have some form of central heating.

The type, tenure, rooms, bedrooms and central heating values for unoccupied dwellings were synthesised by sampling from the (larger) population of occupied households within the OA.


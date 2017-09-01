# Household Microsynthesis

==Work in progress==

## Dependencies

`python3`

### [NomiswebApi](https://github.com/virgesmith/UKCensusAPI)
```
pip3 install git+git://github.com/virgesmith/UKCensusAPI.git
```
### [humanleague](https://github.com/virgesmith/humanleague)
```
pip3 install git+git://github.com/virgesmith/humanleague.git@1.0.1
```

## Testing
```
./setup.py install
./setup.py test
```

## Running

```
python3 scripts/run_microsynth.py
```

# Introduction

This document outlines the methodology and software implementation of a scalable small area microsynthesis of dwellings in a given region. It uses a microsynthesis technique developed by the author (publication in peer review) that uses quasirandom sampling to directly generate non-fractional populations very efficently.

This work also introduces and tests (successfully) a newly-developed extension to the microsynthesis technique that can deal with extra constraints (in this case the fact that a household cannot have more bedrooms than rooms). 

# Terminology

We use the term `unoccupied' in this work to mean a dwelling that is not permanently occupied, or is unoccupied on the census date. 

\begin{tabular}{|l|p{13cm}|}\hline
  \textbf{Category:}  & \textbf{Values} \\\hline 
  Geography:          & (output area) \\\hline 
  Tenure:             & Owned, Mortgaged/shared, Rented social, Rented private, (Communal category) \\\hline  
  Type:               & Detached, Semi, Terrace, Flat/mobile, Communal \\\hline 
  Occupants:          & 1, 2, 3, 4+ \\\hline 
  Rooms:              & 1, 2, 3, 4, 5, 6+ \\\hline 
  Bedrooms:           & 1, 2, 3, 4+ \\\hline 
  CentHeat:           & False, True \\\hline 
  PPerBed:            & \(\le{0.5}\), \((0.5,1]\), \((1,1.5]\), \(>1.5\) \\\hline 
  Composition:        & Single person, Married/civil partnership, Cohabiting couple, Single parent, Multi person, Unoccupied \\\hline 
\end{tabular} \\

Since occupants, rooms and bedrooms are capped (with the final value representing an `...or more' category, there is some imprecision in the microsynthesis:

\begin{itemize}
\item{the count of population in households is lower than the true population estimate.}
\item{the value of persons per bedroom (`PPerBed' above) does not quite match the census data, due to the imprecision inherent in the 4+ categories. This makes it difficult to use it as a link variable between household composition and rooms/bedrooms.\footnote{This mismatch could potentially be used to refine estimates of persons and bedrooms in properties, but is out of scope for the moment.}}
\end{itemize}

# Input Data

The only user input to the model is the geographical area under consideration, e.g. in theory `Newcastle upon Tyne'. In practice the current implementation cannot successfully query nomisweb for it's internal geographical codes at OA level. For Newcastle (and Bradford) these codes are provided in the source code. (See e.g. MSIM2.R line 23 and Geography.R.)

The required 2011 Census tables are automatically downloaded from nomisweb.co.uk via their API. (End users should ensure they have an account and an API key, otherwise data downloads may be incomplete.) \\ Since the data is essentially static, downloads are cached\footnote{Stored by the hash of the API query.}, and subsequent runs on the same geographical area will use the cached data (if available).

\begin{tabular}{|l|l|} \hline  
  \textbf{Table} & \textbf{Description} \\\hline  
  \texttt{LC4402} & Accommodation type by type of central heating in household by tenure \\\hline  
  \texttt{LC4404} & Tenure by household size by number of rooms \\\hline    
  \texttt{LC4405} & Tenure by household size by number of bedrooms \\\hline  
  \texttt{LC4408} & Tenure by number of persons per bedroom in household by household type \\\hline  
  \texttt{LC1105EW} &  Residence type by sex by age \\\hline  
  \texttt{KS401EW} & Dwellings, household spaces and accommodation type \\\hline        
  \texttt{QS420EW} & Communal establishment management and type - Communal establishments \\\hline        
  \texttt{QS421EW} & Communal establishment management and type - People \\\hline        
\end{tabular} \\


Note the following limitations in the input data:
\begin{itemize}
\item{No census table is known that links rooms directly to bedrooms.}
\item{No census data is available that indicated the type or tenure (or size) of unoccupied dwellings.}
\item{No census data is available that indicated the tenure, occupants or size of communal residences.}
\end{itemize}

The Methodology section (\ref{methodology}) explains how these limitations are overcome.

\section{Output Data}\label{outputData}

Example runtime output:

```
> source('~/dev/Mistral/MSIM2.R')
[1] "using cached data: ./data/ba2e68bdbee8f78c22d9ce04f2234f8a.tsv"
[1] "using cached data: ./data/b37393e8090530622135c0b81912a303.tsv"
[1] "using cached data: ./data/8904706b65140065edbc0c88d633afef.tsv"
[1] "using cached data: ./data/807c2ef23848ca32f5924b391c437e2d.tsv"
[1] "using cached data: ./data/4d4c67b0081ef8f944abcc29871b4131.tsv"
[1] "using cached data: ./data/c827514e537cafa57447778b9304ef69.tsv"
[1] "Dwellings: 121894"
[1] "Occupied households: 117153"
[1] "Unoccupied dwellings: 4741"
[1] "Communal residences: 254"
[1] "Total population: 280177"
[1] "Population in occupied households: 271212"
[1] "Population in communal residences: 8965"
[1] "Population lower bound from occupied households: 257127"
[1] "Occupied household population underestimate: 14085"
[1] "assembly time (s):  257.992512464523"
[1] "Checking consistency..."
[1] "Population lower bound from households and communal residences: 266092"
[1] "Overall population underestimate: 14085"
[1] "People per bedroom"
[1] "<=0.5 usim = 33575 , census = 33773"
[1] "(0.5,1] usim = 62937 , census = 60267"
[1] "(1,1.5] usim = 15719 , census = 14271"
[1] ">1.5 usim = 4922 , census = 8842"
[1] "room/bedroom error count: 0"
[1] "Writing microsynthesis to ./data/synHomes.csv"
```

The microsynthesed dwelling population is rendered as a \texttt{csv} file. Each row in the table represents an individual dwelling. The columns contain the categories described in the previous section.

For ease of use, enumerated categories (e.g Tenure) are represented in both text and numeric format. The numeric value is generally the same value used by the census; the text values are either the census text, abbreviated in some cases. The tables below map numeric to text values for these categories.

Since no tenure information is forthcoming for communal residences, the Tenure and TenureName columns are repurposed to store information about the type of the communal residence (see table below). The Tenure values are offset by 100 to avoid confusion.


\begin{center}
\begin{tabular}{|l|l|r|}\hline
  \textbf{Category}  & \textbf{Text}  & \textbf{Value} \\\hline
  Tenure             & Owned & 2 \\
                     & Mortgaged/shared & 3 \\ 
                     & Rented social  & 5 \\  
                     & Rented private & 6 \\  
  (Communal)         & Medical and care establishment: NHS & 102 \\  
					 & Medical and care establishment: Local Authority & 106 \\
					 & Medical and care establishment: Registered Social Landlord/Housing Association & 111 \\
					 & Medical and care establishment: Other & 114 \\
					 & Other establishment: Defence & 122 \\
					 & Other establishment: Prison service & 123 \\
				     & Other establishment: Approved premises (probation/bail hostel) & 124 \\
				     & Other establishment: Detention centres and other detention & 125 \\
				     & Other establishment: Education & 126 \\
				     & Other establishment: Hotel: guest house; B\&B; youth hostel & 127 \\
				     & Other establishment: Hostel or temporary shelter for the homeless & 128 \\
				     & Other establishment: Holiday accommodation (for example holiday parks) & 129 \\
				     & Other establishment: Other travel or temporary accommodation & 130 \\
				     & Other establishment: Religious & 131 \\
				     & Other establishment: Staff/worker accommodation only & 132 \\
				     & Other establishment: Other & 133 \\
				     & Establishment not stated  & 134 \\\hline  
  Type               & Detached & 2 \\
                     & Semi & 3 \\ 
                     & Terrace  & 4 \\  
                     & Flat/mobile & 5 \\   
                     & Communal & 6 \\\hline  
  PPerBed            & \(\le{0.5}\) & 1 \\
                     & \((0.5,1]\)& 2 \\ 
                     & \((1,1.5]\) & 3 \\  
                     & \(>1.5\) & 4 \\\hline  
  Composition        & Single person & 1 \\
                     & Married/civil partnership & 2 \\ 
                     & Cohabiting couple & 3 \\  
                     & Single parent & 4 \\   
                     & Multi person & 5 \\   
                     & Unoccupied & 6 \\\hline  
\end{tabular} \\
\end{center}

\section{Microsynthesis methodology}\label{methodology}
The microsynthesis methodology can be split into three distinct parts:

\subsection{Microsynthesis of Occupied Dwellings}
All categories are constrained at a minimum by output area (OA) and dwelling tenure, note also: 
\begin{itemize}
\item{central heating assignment - no further constraint}
\item{occupants/rooms/bedrooms assignment - bedrooms cannot exceed rooms}
\item{household composition assignment - single occupant households are assigned directly, others are synthesised}
\end{itemize}

## Addition of Communal Residences

Census data provides a count of the number of, and total occupants of, each type of communal residence within an an OA. For each communal residence of each type in each OA, an entry is inserted into the overall dwelling population.

Note the assumptions that were made:
\begin{itemize}
\item{Where there are multiple communal residences of the same type in an OA, the occupants are split equally (rounded to integer) across the residences.}
\item{The tenure of communal residences in not known, not deemed sufficiently important to synthesise. The type of the communal residence is assigned to this field.}
\item{The composition of residences is assigned a single value: `Communal'.}
\item{The type of communal residences is assigned a single value: `Multi-person'.}
\item{All communal residences are assumed to have some form of central heating.}
\end{itemize}

\subsection{Microsynthesis of Unoccupied Dwellings}

The microsynthesis is constrained only by OA. Note the assumptions that were made:

\begin{itemize}
\item{Zero occupants, and thus \(\le0.5\) persons per bedroom, were assigned to each dwelling.}
\item{The type, tenure, rooms, bedrooms and central heating of the dwellings are not given in census data but are deemed sufficiently important to synthesise.}
\item{The composition opf these dwellings is assigned the value `Unoccupied'.}
\item{All communal residences are assumed to have some form of central heating.}
\end{itemize}

The type, tenure, rooms, bedrooms and central heating values for unoccupied dwellings were synthesised by sampling from the (larger) population of occupied households within the OA.


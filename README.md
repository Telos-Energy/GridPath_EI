# GridPath Eastern Interconnect Resource Adequacy Study - User Guide
Companion code for running the Eastern Interconnect (EI) Resource Adequacy (RA) Study run using GridPath.

GridPath is an open-source, Python-based system planning platform. The platform is developed and maintained by Sylvan Energy Analytics.

## Required and Recommended Installations
GridPath is compatible with Python versions with Python versions 3.9, 3.10, and 3.11. The EI RA Study is compatible with v2025.5.0 of GridPath. Instructions for downloading Python and GridPath are found on the GridPath [Installation Documentation.](https://github.com/blue-marble/gridpath)

Additional software is required for compatibility with the detailed instructions in this User Guide. [Microsoft Visual Studio (VS) Code](https://code.visualstudio.com) is required to run each step of the GridPath simulation using the `launch.json` file.

The inputs and outputs of the EI RA Study are stored in an SQL database in multiple steps of the simulation process. A SQL viewer such as [SQLiteStuido] is recommended to view SQL data stored in `.db` files. 

## How to Run the EI RA Study

### Preparation
1. Clone the GridPath EI RA User Guide repository and open the launch.json file.
2. Activate the GridPath virtual environment where GridPath is installed.
   - In VS Code, a virtual environment can be activated with 'Ctrl+Shift+P' and searching "Python: Select an Interpreter". Navigate to the virtual environemnt folder and select the python executable in the Scripts folder. 
3. Adjust all paths in the [`launch.json`](.vscode/launch.json) file to desired locations on your local machine.
4. Open the Debug menu in VS Code to access the different Debug profiles specified in the `lanuch.json` file. The dropdown menu in the top left corner should show all possible 'Gridpath: ' steps.

### Running GridPath through the `launch.json`
A GridPath simulation requires a SQL Database populated with carefully formatted input tables. The input tables must contain values for all modules specified  (e.g. reserves, transmission). This repository facilitates the multiple steps in an end-to-end run, beginning with creating a SQL database with input data to populating the database with results. 

#### Selecting a Scenario from [`scenarios.csv`](scenarios.csv)
In GridPath, a 'scenario' represents a collection of input data to be joined together in a simulation. The EI RA Study used 3 main scenarios: 

| Scenario | Scenario Description | Important Subscenario Data Changed |
|----------|----------| ----------- |
| 1 | Full Technical Limits Transmission | _N/A_
| 2 | RA Import Limited Transmission  | transmission_simultaneous_flow_limit_scenario_id
| 3 | No Interregional Transmission | transmission_portfolio_scenario_id

In the `scenarios.csv` file, the column headers represent the different scenario names, with the rows representing each set of input data associated with the scenario. The IDs in each cell *must* be correlated with input data populated in the SQL database under the same ID. 

Once the `launch.json` file is updated with appropriate local paths for the SQL database and CSV results, the following steps can be run in order for the 'scenario' chosen:
1. Create the Database. This step will create an empty SQL database with tables structured for the storage of input and output data.
2. Load CSVs into Database. This step will pull the input CSVs from the locations specified in the `csv_structure.csv`. The CSVs are located in the repo folders `project`, `transmisssion`, etc.
3. Load Scenarios: This step will pull in the scenarios specified in the `scenarios.csv` file. 
4. Run End to End: This step options will run the GridPath simulation under different sets of run options.
    - All Steps, All Results: Print full results for all hours of the simulation. Only recommended for short cases (<= 1 year) with few iterations (<= 5 iterations)
    - All Steps,  USE Results Only: Print full results only for subproblems where Unserved Energy was observed. In all other subproblems, only summary files will be printed. Highly recommended for large case runs.
    - Get Inputs Only: Only run the 'Get Inputs' step. This step takes the input tables from the SQL Database and creates folders of CSVs specific to each subproblem
    - Run Scenario (All Results): Only run the 'Run Scenario' step. This step builds models for each subproblem before solving with the downloaded solver. All results will be printed for all subproblems.
    - Run Scenario (USE Results Only): Only run the 'Run Scenario' step. This step builds models for each subproblem before solving with the downloaded solver. All results will only be printed for subproblems where Unserved Energy was observed. In all other subproblems, only summary files will be printed.
    - Import Results Only: Only run the 'Import Results' step. This step imports the result CSVs printed in the 'Run Scenario' step into the SQL Database
    - Process Results: Only run the 'Process Results' step. This step aggregates the entire scenario's imported results into summary tables located in the SQL Database.

## Input Data for the EI RA Study

### Generator Capacity (EIA Form 860)
EIA Form 860 is posted annually and contains characteristics for all surveyed generators in the United States. The latest data can be found on the [EIA Website.](https://www.eia.gov/electricity/data/eia860/)

#### Plant and Generator Data
Within the ZIP file download, the two files used in the EI RA Study were the 'Plant' and 'Generator' files.
- Plant Data: Balancing Authority Code, State, County
- Generator Data: Technology, Prime Mover, Summer Capacity, Winter Capacity, Status, Retirement Year, Sync to Grid
    - Operable Generator Status Codes Included: OP (Operating), OA (Out of Service but Returning in Next Calendar Year)
    - Proposed Generator Status Codes Included: U (Under Construction, <50% Complete), V (Under Construction, >50% Complete), TS (Construction Complete, but Not Commercial)
    - Retirements Excluded: Retirement Year <= 2028

#### [BA/State Map](EIA_Generator_Mapping/Maps/State_BA_Map.csv)
Once the Plant and Generator data is combined and filtered, a BA/State map aggregated generators to regions, with some BA/State combinations further split out by County when neccessary.

#### [Fuel Type Map](EIA_Generator_Mapping/Maps/Fuel_Type_Map.csv)
The combinations of fuel technology (e.g. Natural Gas, Nuclear, Petroleum Liquids, etc.) and Prime Mover (e.g. Combined-Cycle, Steam Turbine, etc.) were mapped to 13 simple fuel types. The availability of secondary fuel for Natural Gas Generators was assigned a separate dual-fuel category.

#### Seasonal Capacity (Using Weather Derates)
GridPath does not natively support variations in specified capacity from one hour of the year to another. Instead, seasonal capacity derates (or uprates) were handled through [weather-dependent outage derates](project/generator_availability/exogenous_weather_horizons/). In the EI RA Study, the specified capacity was always set to the summer capacity of a generator. A weather derate based was then implemented depending the seasonal capacity variations. Under this implementation, the weather derate would always equal 1 during summer months, and then greater or less than 1 depending on the direction of the summer-to-winter capacity adjustment.

### Generator Outages (NERC GADS Brochure)
NERC publishes a brochure of forced outage statistics that are averaged over the entire North American generation fleet and split into categories of fuel type and generator size. In the EI RA study, each EIA generator was assigned a forced outage rate according to their associated [NERC GADS bin.](EIA_Generator_Mapping/Maps/GADS_Data_2019_2023.csv)

#### GridPath Data Toolkit Outage Sampling
 The availability input module of Data Toolkit aggregates generator-specific forced outage data into forced outage profiles for generalized resource groups. In the EI RA study, the EIA generators and the associated NERC GADS forced outage factors were input into the Data Toolkit and output as region/fuel type [forced outage profiles](project/generator_availability/exogenous_independent_horizons).

### [Transfer Limits](transmission/transmission_limits) (NERC ITCS Technical Limits)

#### Seasonal Transfer Limits (Using Monthly Derates)
Similar to seasonal generator capacities, seasonal transmission capacities were calcualted as a winter derate/uprate compared to summer capacity values. GridPath supports [availability derates](transmission/transmission_hurdle_rates/transmission_availability/transmission_availability_exogenous) for transmission objects on a monthly basis.

### [Operating Reserves Margins](reserves/minimum_reserves/reserve_details/2_largest_gen_percentage/percentage.csv)

Telos method of reserve percentage as ratio of largest gen to peak load
Rather than enforce a static percentage of load as reserves across, the EI RA study utilized a custom reserve percentage for each region. The percentage value was calculated as the ratio of the region’s largest generator over the peak input load. For regions such as PJM with multiple sub-BA regions modeled (PJM-E, PJM-S, PJM-W), the peak load was calculated as a coincident peak.

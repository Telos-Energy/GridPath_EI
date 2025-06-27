import pandas as pd
import os
import numpy as np
import datetime

example_input_excel = r"G:\Shared drives\Telos Energy, Main\Clients\ESIG\ESIG Interregional Phase II\2_Inputs and Assumptions\Non-SPP Inputs & Assumptions\Resource Mix\2029_2030 Mix\2030 Non-SPP Capacity Mix_3_1_Generator_Y2022_v1.xlsx"

mapping_input_excel = r"G:\Shared drives\Telos Energy, Main\Clients\ESIG\ESIG Interregional Phase II\2_Inputs and Assumptions\Non-SPP Inputs & Assumptions\Resource Mix\2029_2030 Mix\Base 2022 EIA 860\EIA_860_Unit_Database_v1.xlsx"

eia_data_path = r"G:\Shared drives\Telos Energy, Main\Clients\GridLab\EI GridPath RA\3_Inputs and Assumptions\EIA 860 2023 Data"

output_path = (
    r"C:\Users\SamHostetter\Documents\GitHub\EI_RA_Gridpath\EIA Generator Mapping"
)


mapping_input = pd.read_excel(
    mapping_input_excel, sheet_name="EIA_860_NERC", usecols="C:H"
)

data_year = 2028

## EIA Generator Data

eia_data_operable = pd.read_excel(
    os.path.join(eia_data_path, "3_1_Generator_Y2023.xlsx"),
    sheet_name="Operable",
    header=1,
)

eia_data_operable["Planned Retirement Year"] = pd.to_numeric(
    eia_data_operable["Planned Retirement Year"], errors="coerce"
)
eia_data_operable["Install Year"] = pd.to_numeric(
    eia_data_operable["Operating Year"], errors="coerce"
)

eia_data_operable["Summer Capacity (MW)"] = pd.to_numeric(
    eia_data_operable["Summer Capacity (MW)"], errors="coerce"
)
eia_data_operable["Winter Capacity (MW)"] = pd.to_numeric(
    eia_data_operable["Winter Capacity (MW)"], errors="coerce"
)
eia_data_operable["Source"] = "Operable"

eia_data_proposed = pd.read_excel(
    os.path.join(eia_data_path, "3_1_Generator_Y2023.xlsx"),
    sheet_name="Proposed",
    header=1,
)

eia_data_proposed["Install Year"] = pd.to_numeric(
    eia_data_proposed["Current Year"], errors="coerce"
)
eia_data_proposed["Planned Retirement Year"] = pd.to_numeric(None, errors="coerce")
eia_data_proposed["Synchronized to Transmission Grid"] = ""
eia_data_proposed["Summer Capacity (MW)"] = pd.to_numeric(
    eia_data_proposed["Summer Capacity (MW)"], errors="coerce"
)
eia_data_proposed["Winter Capacity (MW)"] = pd.to_numeric(
    eia_data_proposed["Winter Capacity (MW)"], errors="coerce"
)
eia_data_proposed["Source"] = "Proposed"

eia_data_columns = [
    "Plant Code",
    "Generator ID",
    "Plant Name",
    "Status",
    "Install Year",
    "Planned Retirement Year",
    "Synchronized to Transmission Grid",
    "Summer Capacity (MW)",
    "Winter Capacity (MW)",
    "Energy Source 1",
    "Energy Source 2",
    "Technology",
    "Prime Mover",
    "Source",
]

eia_data_column_names = [
    "EIA_Plant_ID",
    "EIA_Generator_ID",
    "EIA_Plant_Name",
    "Status",
    "Install_Year",
    "Retirement_Year",
    "Sync_To_Grid",
    "Summer_Capacity_MW",
    "Winter_Capacity_MW",
    "Primary_Energy_Source",
    "Secondary_Energy_Source",
    "Technology",
    "Prime_Mover",
    "Source",
]

eia_data_selected = pd.concat(
    [eia_data_operable[eia_data_columns], eia_data_proposed[eia_data_columns]]
).rename(columns=dict(zip(eia_data_columns, eia_data_column_names)))

## EIA Plant Data
eia_plant_data = pd.read_excel(
    os.path.join(eia_data_path, "2___Plant_Y2023.xlsx"),
    sheet_name="Plant",
    header=1,
)

eia_plant_data_columns = [
    "Plant Code",
    "Latitude",
    "Longitude",
    "NERC Region",
    "Balancing Authority Code",
    "State",
    "County",
    "Transmission or Distribution System Owner",
]
eia_plant_data_column_names = [
    "EIA_Plant_ID",
    "Latitude",
    "Longitude",
    "NERC_Region",
    "BA_Code",
    "State",
    "County",
    "Transmission_Owner",
]

eia_plant_data_selected = eia_plant_data[eia_plant_data_columns].rename(
    columns=dict(zip(eia_plant_data_columns, eia_plant_data_column_names))
)

## Existing Project Topology Data
project_topology_columns = ["Plant Code", "Generator ID", "Source/Sink", "Type Simple"]
project_topology_column_names = [
    "EIA_Plant_ID",
    "EIA_Generator_ID",
    "Region",
    "Type",
]

project_topology_data_operable = pd.read_excel(
    example_input_excel,
    header=1,
    sheet_name="Operable",
    usecols=project_topology_columns,
).rename(columns=dict(zip(project_topology_columns, project_topology_column_names)))

project_topology_data_proposed = pd.read_excel(
    example_input_excel,
    header=1,
    sheet_name="Proposed",
    usecols=project_topology_columns,
).rename(columns=dict(zip(project_topology_columns, project_topology_column_names)))

project_topology_data = pd.concat(
    [project_topology_data_operable, project_topology_data_proposed]
)

## Merge all data together
eia_generator_data = eia_data_selected.merge(eia_plant_data_selected, how="left").merge(
    project_topology_data, how="left"
)

eia_generator_data["Retired_Flag"] = (
    eia_generator_data["Retirement_Year"] <= data_year
).astype(int)

eia_generator_data["New_Install_Flag"] = (
    (eia_generator_data["Install_Year"] >= pd.Timestamp.today().year)
    & (eia_generator_data["Install_Year"] <= data_year)
).astype(int)

# Existing State/BA Code Mapping
state_ba_map = pd.read_csv(os.path.join(output_path, "Maps", "State_BA_Map.csv"))

eia_generator_data_mapped = eia_generator_data.merge(state_ba_map, how="left")

# Fill in previous data's region if planning region equals "County"
eia_generator_data_mapped["Planning_Region"] = np.select(
    condlist=[
        eia_generator_data_mapped["State_BA_Region"] == "County",
        eia_generator_data_mapped["State_BA_Region"] != "County",
    ],
    choicelist=[
        eia_generator_data_mapped["Region"],
        eia_generator_data_mapped["State_BA_Region"],
    ],
)

# Strip leading zeros to prevent merge conflicts
eia_generator_data_mapped["EIA_Generator_ID"] = eia_generator_data_mapped[
    "EIA_Generator_ID"
].str.lstrip("0")

# Fuel Mappings
fuel_type_map = pd.read_csv(os.path.join(output_path, "Maps", "Fuel_Type_Map.csv"))

eia_generator_data_ftype = eia_generator_data_mapped.merge(fuel_type_map, how="left")

## Custom Columns
# Remove Out of Scope Regions
eia_generator_data_ftype = eia_generator_data_ftype[
    ~eia_generator_data_ftype["Planning_Region"].isin(["Out of Scope", "Exclude"])
]

eia_generator_data_ftype["Dual_Fuel"] = np.select(
    condlist=[
        (eia_generator_data_ftype["Primary_Energy_Source"].isin(["NG"]))
        & (
            eia_generator_data_ftype["Secondary_Energy_Source"].isin(
                ["DFO", "JF", "KER", "PG", "WO", "RFO"]
            )
        )
    ],
    choicelist=[1],
    default=0,
)

eia_generator_data_ftype["Interconnect"] = np.select(
    condlist=[
        eia_generator_data_ftype["Planning_Region"].isin(
            [
                "ISONE",
                "MISO-C",
                "MISO-E",
                "MISO-S",
                "MISO-W",
                "NYISO",
                "PJM-E",
                "PJM-S",
                "PJM-W",
                "SERC-C",
                "SERC-E",
                "SERC-FL",
                "SERC-SE",
                "SPP-N",
                "SPP-S",
            ]
        ),
        eia_generator_data_ftype["Planning_Region"] == "ERCOT",
    ],
    choicelist=["Eastern", "Texas"],
    default="Western",
)

# Re-ID duplicates
eia_generator_data_ftype["EIA_Generator_ID"] = np.where(
    (
        (eia_generator_data_ftype["EIA_Plant_ID"] == 56032)
        & (eia_generator_data_ftype["Summer_Capacity_MW"] == 48.1)
    ),
    2,
    eia_generator_data_ftype["EIA_Generator_ID"],
)

# Export raw data
eia_generator_data_ftype.to_csv(
    os.path.join(output_path, "EIA_Generator_Mapping_Raw.csv"), index=False
)

## Map adhoc Data
adhoc_map = (
    pd.read_csv(os.path.join(output_path, "Maps", "Adhoc_Map_Final.csv"))
    .set_index(["EIA_Plant_ID", "EIA_Generator_ID"])
    .sort_index()
)

eia_generator_data_adhoc = eia_generator_data_ftype.set_index(
    ["EIA_Plant_ID", "EIA_Generator_ID"]
).sort_index()

# eia_generator_data_adhoc.update(adhoc_map)

eia_generator_data_adhoc = adhoc_map.combine_first(
    eia_generator_data_adhoc
).reset_index()

# Export adhoc data
eia_generator_data_adhoc.to_csv(
    os.path.join(output_path, "EIA_Generator_Mapping_Adhoc.csv"), index=False
)

# Filter to final data
filter_list = [
    lambda df: df["Status"].isin(["OP", "OA", "U", "V", "TS"]),
    lambda df: df["Sync_To_Grid"] != "N",
    lambda df: df["Retired_Flag"] != 1,
]

eia_generator_data_filtered = eia_generator_data_adhoc.copy()

for f in filter_list:
    eia_generator_data_filtered = eia_generator_data_filtered[
        f(eia_generator_data_filtered)
    ]

# Export any generators missing a planning region that make it through the filters
missing_generators = eia_generator_data_filtered[
    (eia_generator_data_filtered["Planning_Region"].isna())
    & (eia_generator_data_filtered["Retired_Flag"] != 0)
]

missing_generators.to_csv(
    os.path.join(output_path, "Analysis", "Missing_Generators.csv"), index=False
)

## Create Gridpath columns and then export as final\

# Convert Region column into GridPath Region Column
eia_generator_data_filtered["GridPath_Region"] = (
    eia_generator_data_filtered["Planning_Region"]
    .str.replace("-", "_")
    .str.replace(" ", "_")
    .str.upper()
)

# Convert Fuel Type Simple into Gridpath Fuel Type
eia_generator_data_filtered["GridPath_Fuel_Type"] = np.select(
    condlist=[
        (eia_generator_data_filtered["Fuel_Type_Simple"] == "GAS")
        & (eia_generator_data_filtered["Dual_Fuel"] == 1),
        (eia_generator_data_filtered["Fuel_Type_Simple"] == "GAS")
        & (eia_generator_data_filtered["Dual_Fuel"] == 0),
    ],
    choicelist=["GAS_DUAL_FUEL", "GAS_SINGLE_FUEL"],
    default=None,
)

eia_generator_data_filtered["GridPath_Fuel_Type"] = (
    eia_generator_data_filtered["GridPath_Fuel_Type"]
    .astype(object)
    .fillna(eia_generator_data_filtered["Fuel_Type_Simple"])
    .str.replace(" ", "_")
)

eia_generator_data_filtered["GridPath_Type"] = (
    eia_generator_data_filtered["GridPath_Region"]
    + "_"
    + eia_generator_data_filtered["GridPath_Fuel_Type"]
)

# GADS Outage Data Mappings
gads_outage_data = pd.read_csv(
    os.path.join(output_path, "Maps", "GADS_Data_2019_2023.csv")
)

eia_generator_data_detail_gads = eia_generator_data_filtered.merge(
    gads_outage_data[["GridPath_Fuel_Type", "Min_Value", "Max_Value", "FOF", "MOF"]],
    how="left",
    indicator=True,
)

## Create common capacity column if one is missing
eia_generator_data_detail_gads["Capacity_MW"] = eia_generator_data_detail_gads[
    "Winter_Capacity_MW"
].fillna(eia_generator_data_detail_gads["Summer_Capacity_MW"])

# After left join on GridPath Fuel Type, only keep rows where capacity is within bounds OR GADS data did not have a matching fuel type
eia_generator_data_final_gads = eia_generator_data_detail_gads[
    (
        (
            eia_generator_data_detail_gads["Capacity_MW"]
            >= eia_generator_data_detail_gads["Min_Value"]
        )
        & (
            eia_generator_data_detail_gads["Capacity_MW"]
            < eia_generator_data_detail_gads["Max_Value"]
        )
    )
    | (eia_generator_data_detail_gads["_merge"] == "left_only")
]

## Select columns for export
eia_generator_data_final_columns = [
    "EIA_Plant_ID",
    "EIA_Generator_ID",
    "EIA_Plant_Name",
    "Status",
    "Summer_Capacity_MW",
    "Winter_Capacity_MW",
    "Interconnect",
    "Latitude",
    "Longitude",
    "State",
    "NERC_Region",
    "BA_Code",
    "Primary_Energy_Source",
    "Secondary_Energy_Source",
    "Prime_Mover",
    "Dual_Fuel",
    "Fuel_Type_Detail",
    "Fuel_Type_Simple",
    "Retired_Flag",
    "Retirement_Year",
    "New_Install_Flag",
    "Install_Year",
    "Planning_Region",
    "GridPath_Region",
    "GridPath_Fuel_Type",
    "GridPath_Type",
    "FOF",
    "MOF",
]

# Export final table
eia_generator_data_final_gads[eia_generator_data_final_columns].to_csv(
    os.path.join(output_path, "EIA_Generator_Mapping_Final.csv"), index=False
)

## ADHOC ANALYSIS

eia_generator_data_final_pivot = eia_generator_data_final_gads.pivot_table(
    index=["GridPath_Region"],
    columns="GridPath_Fuel_Type",
    values=["Summer_Capacity_MW", "Winter_Capacity_MW"],
    aggfunc="sum",
)

eia_generator_data_final_pivot.to_csv(
    os.path.join(output_path, "Analysis", "Capacity_Pivot.csv"),
    index=False,
)

eia_data_selected_test = eia_generator_data_ftype.merge(
    eia_generator_data_final_gads[["EIA_Plant_ID", "EIA_Generator_ID"]],
    how="left",
    indicator=True,
)

eia_data_removed = eia_data_selected_test[
    (eia_data_selected_test["_merge"] == "left_only")
]

eia_data_removed.to_csv(
    os.path.join(output_path, "Analysis", "Removed_Proposed_Generators.csv"),
    index=False,
)

print("done")

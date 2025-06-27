import pandas as pd
import os
import numpy as np

eia_generator_data_path = (
    r"C:\Users\SamHostetter\Documents\GitHub\EI_RA_Gridpath\EIA Generator Mapping"
)

output_path = (
    r"C:\Users\SamHostetter\Documents\GitHub\EI_RA_Gridpath\Gridpath CSV Creation"
)

eia_generator_data = pd.read_csv(
    os.path.join(eia_generator_data_path, "EIA_Generator_Mapping_Final.csv")
)

eia_generator_data = eia_generator_data[eia_generator_data["Retired_Flag"] != 1]

eia_generator_data["Summer_Capacity_MW"] = pd.to_numeric(
    eia_generator_data["Summer_Capacity_MW"], errors="coerce"
)
eia_generator_data["Winter_Capacity_MW"] = pd.to_numeric(
    eia_generator_data["Winter_Capacity_MW"], errors="coerce"
)

eia_generator_capacities = (
    eia_generator_data.groupby("GridPath_Type")[
        ["Summer_Capacity_MW", "Winter_Capacity_MW"]
    ]
    .sum()
    .reset_index()
)

generator_all = pd.read_csv(os.path.join(output_path, "generator_all.csv"))

new_generator_all = generator_all.merge(
    eia_generator_capacities, how="left", left_on="project", right_on="GridPath_Type"
)

new_generator_all["summer_specified_capacity_mw"] = new_generator_all[
    "Summer_Capacity_MW"
].fillna(new_generator_all["summer_specified_capacity_mw"])

new_generator_all["winter_specified_capacity_mw"] = new_generator_all[
    "Winter_Capacity_MW"
].fillna(new_generator_all["winter_specified_capacity_mw"])

# Change summer capacity from 0 to 1 to prevent derate scaling on 0
# e.g: 0 * seasonal derate = 0 winter capacity always

new_generator_all.loc[
    (new_generator_all["summer_specified_capacity_mw"] == 0)
    & (new_generator_all["winter_specified_capacity_mw"] > 0),
    ["summer_specified_capacity_mw"],
] = 1

new_generator_all["summer_to_winter_derate"] = np.where(
    new_generator_all["summer_specified_capacity_mw"] != 0,
    new_generator_all["winter_specified_capacity_mw"]
    / new_generator_all["summer_specified_capacity_mw"],
    np.nan,
)

new_generator_all["specified_stor_capacity_mwh"] = np.select(
    condlist=[
        new_generator_all["technology"] == "BATTERY_STORAGE",
        new_generator_all["technology"] == "PUMPED_STORAGE",
    ],
    choicelist=[
        new_generator_all["summer_specified_capacity_mw"] * 4,
        new_generator_all["summer_specified_capacity_mw"] * 12,
    ],
    default=np.nan,
)

new_generator_all_columns = [
    "project",
    "NERC_Name",
    "PLEXOS_Name",
    "GADS_Name",
    "period",
    "load_zone",
    "technology",
    "capacity_type",
    "operational_type",
    "balancing_type_project",
    "reserves_flag",
    "specified_capacity_mw",
    "specified_capacity_mwh",
    "summer_specified_capacity_mw",
    "winter_specified_capacity_mw",
    "summer_to_winter_derate",
    "specified_stor_capacity_mwh",
    "variable_om_cost_per_mwh",
    "heat_rate_curves_scenario_id",
    "load_point_fraction",
    "average_heat_rate_mmbtu_per_mwh",
    "min_stable_level_fraction",
    "charging_efficiency",
    "discharging_efficiency",
    "variable_generator_profile_scenario_id",
    "curtailment_cost_per_pwh",
    "hydro_operational_chars_scenario_id",
    "availability_type",
    "exogenous_availability_independent_scenario_id",
    "exogenous_availability_weather_scenario_id",
]

new_generator_all[new_generator_all_columns].to_csv(
    os.path.join(output_path, "eia_generator_all.csv"), index=False
)

print("done")

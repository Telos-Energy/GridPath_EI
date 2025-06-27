import pandas as pd
import os
import numpy as np
import datetime
from pathlib import Path

input_path = r"G:\Shared drives\Telos Energy, Main\Clients\GridLab\EI GridPath RA\3_Inputs and Assumptions\EIA 930 Data"


gridpath_path = r"C:\Users\SamHostetter\Documents\GitHub\EI_RA_Gridpath"
generator_all_path = "Gridpath CSV Creation\generator_all.csv"

subscenario_id = "1"
subscenario_name = "ra_toolkit"

output_path = r"C:\Users\SamHostetter\Documents\GitHub\EI_RA_Gridpath\project\Hydro Operational Chars"

csv_list = Path(input_path).glob("*.csv")

interchange_data = pd.DataFrame({})
for csv in csv_list:
    df = pd.read_csv(csv)
    df = df[df["Balancing Authority"].isin(["SWPP", "MISO", "NYIS", "ISNE"])]
    interchange_data = pd.concat([interchange_data, df])

interchange_data["Datetime"] = pd.to_datetime(
    interchange_data["Local Time at End of Hour"]
)
interchange_data["Date"] = interchange_data["Datetime"].dt.date

interchange_data["Day_of_Year"] = interchange_data["Datetime"].dt.day_of_year.astype(
    object
)

interchange_data = interchange_data.rename(
    columns={
        "Balancing Authority": "BA_From",
        "Directly Interconnected Balancing Authority": "BA_To",
        "Interchange (MW)": "Interchange_MW",
    }
)

select_ba_data = interchange_data[
    interchange_data["BA_From"].isin(["MISO", "SWPP", "NYIS", "ISNE"])
]

gridpath_proxy_load_zones = [
    "SPP_S",
    "SPP_N",
    "SASK_POWER",
    "MB_HYDRO",
    "IESO",
    "HQ",
    "MARITIMES",
]

select_ba_data["Proxy_Region"] = np.select(
    condlist=[
        select_ba_data["BA_To"].isin(["EPE", "ERCO", "PNM", "PSCO", "SPA"]),
        select_ba_data["BA_To"].isin(["WACM", "WAUW"]),
        select_ba_data["BA_To"].isin(["SPC"]),
        select_ba_data["BA_To"].isin(["MHEB"]),
        select_ba_data["BA_To"].isin(["IESO"]),
        select_ba_data["BA_To"].isin(["HQT"]),
        select_ba_data["BA_To"].isin(["NBSO"]),
    ],
    choicelist=gridpath_proxy_load_zones,
)
select_ba_data["Season"] = np.select(
    condlist=[
        select_ba_data["Datetime"].dt.month.isin([5, 6, 7, 8, 9, 10]),
        select_ba_data["Datetime"].dt.month.isin([1, 2, 3, 4, 11, 12]),
    ],
    choicelist=["Summer", "Winter"],
)

select_ba_data[select_ba_data.select_dtypes(include="number").columns] *= -1

hourly_interchange_pivot = select_ba_data[
    select_ba_data["Proxy_Region"].isin(gridpath_proxy_load_zones)
].pivot_table(
    index=["Datetime", "Date"],
    columns=["Season", "Proxy_Region"],
    values="Interchange_MW",
    aggfunc="sum",
)

season_proxy_limits = (
    hourly_interchange_pivot.quantile(0.99)
    .reset_index()
    .rename(columns={0.99: "Quantile_Max"})
)


# # Ad hoc add in MB to IESO transmission capability
# season_proxy_limits["Quantile_Max_Adj"] = np.where(
#     (season_proxy_limits["Proxy_Region"] == "MB_HYDRO")
#     & (season_proxy_limits["Season"] == "Summer"),
#     season_proxy_limits["Quantile_Max"] + 1306,
#     season_proxy_limits["Quantile_Max"],
# )

# season_proxy_limits["Quantile_Max_Adj"] = np.where(
#     (season_proxy_limits["Proxy_Region"] == "MB_HYDRO")
#     & (season_proxy_limits["Season"] == "Winter"),
#     season_proxy_limits["Quantile_Max"] + 2206,
#     season_proxy_limits["Quantile_Max"],
# )

generator_all_update = (
    season_proxy_limits.pivot_table(
        index="Proxy_Region", columns="Season", values="Quantile_Max"
    )
    .reset_index()
    .rename(
        columns={
            "Proxy_Region": "load_zone",
            "Summer": "summer_specified_capacity_mw",
            "Winter": "winter_specified_capacity_mw",
        }
    )
)

# Ad hoc add in MB to IESO transmission capability
# generator_all_update[generator_all_update.select_dtypes(include="number").columns] *= -1
# generator_all_update["summer_specified_capacity_mw"] = np.where(
#     generator_all_update["load_zone"] == "MB_HYDRO",
#     generator_all_update["summer_specified_capacity_mw"] + 1306,
#     generator_all_update["summer_specified_capacity_mw"],
# )

# generator_all_update["winter_specified_capacity_mw"] = np.where(
#     generator_all_update["load_zone"] == "MB_HYDRO",
#     generator_all_update["winter_specified_capacity_mw"] + 2206,
#     generator_all_update["winter_specified_capacity_mw"],
# )

generator_all_update["project"] = generator_all_update["load_zone"] + "_PROXY_GEN"
generator_all_update["operational_type"] = "gen_hydro"
generator_all_update["hydro_operational_chars_scenario_id"] = 1
generator_all_update["summer_to_winter_derate"] = (
    generator_all_update["winter_specified_capacity_mw"]
    / generator_all_update["summer_specified_capacity_mw"]
)
generator_all_update = generator_all_update.set_index("project")

generator_all_orginal = pd.read_csv(os.path.join(gridpath_path, generator_all_path))
original_columns = generator_all_orginal.columns
generator_all_orginal = generator_all_orginal.set_index("project")
generator_all = generator_all_update.combine_first(generator_all_orginal).reset_index()[
    original_columns
]
generator_all.to_csv(os.path.join(gridpath_path, generator_all_path), index=False)

daily_interchange_data = (
    select_ba_data[select_ba_data["Proxy_Region"].isin(gridpath_proxy_load_zones)]
    .groupby(["Date", "Day_of_Year", "Season", "Proxy_Region"])["Interchange_MW"]
    .sum()
    .reset_index()
).merge(season_proxy_limits)

daily_interchange_data["Interchange_Avg"] = (
    daily_interchange_data["Interchange_MW"] / 24
).clip(lower=10)

daily_interchange_data["average_power_fraction"] = (
    daily_interchange_data["Interchange_Avg"] / daily_interchange_data["Quantile_Max"]
).clip(upper=1)

daily_interchange_data_statistics = daily_interchange_data.groupby(["Proxy_Region"])[
    "average_power_fraction"
].agg(["min", "median", "max"])

daily_interchange_data_statistics.to_csv(
    os.path.join(
        gridpath_path,
        "EIA Generator Mapping",
        "Analysis",
        "Daily_Interchange_Statistics.csv",
    )
)

random_average_power_fraction = (
    daily_interchange_data.groupby(["Proxy_Region", "Day_of_Year"])[
        "average_power_fraction"
    ]
    .apply(lambda x: x.sample(1, random_state=1).iloc[0], include_groups=False)
    .reset_index()
)

max_average_power_fraction = (
    daily_interchange_data.groupby(["Proxy_Region", "Day_of_Year"])[
        "average_power_fraction"
    ]
    .max()
    .reset_index()
)

for load_zone in gridpath_proxy_load_zones:
    avg_power_fraction_df = random_average_power_fraction[
        random_average_power_fraction["Proxy_Region"] == load_zone
    ]
    hydro_operational_chars_df = pd.DataFrame(
        {
            "weather_iteration": 0,
            "hydro_iteration": 1,
            "stage_id": 1,
            "balancing_type_project": "day",
            "horizon": avg_power_fraction_df["Day_of_Year"],
            "average_power_fraction": avg_power_fraction_df["average_power_fraction"],
            "min_power_fraction": 0,
            "max_power_fraction": 1,
        }
    )

    hydro_operational_chars_df.to_csv(
        os.path.join(
            output_path,
            "-".join(
                [load_zone + "_PROXY_GEN", subscenario_id, subscenario_name + ".csv"]
            ),
        ),
        index=False,
    )

    hydro_iteration_df = pd.DataFrame(
        {"varies_by_weather_iteration": [0], "varies_by_hydro_iteration": [1]}
    )

    hydro_iteration_df.to_csv(
        os.path.join(
            output_path,
            "iterations",
            "-".join(
                [load_zone + "_PROXY_GEN", subscenario_id, subscenario_name + ".csv"]
            ),
        ),
        index=False,
    )

print("stop")

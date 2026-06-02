# This file reads in cases fromm master_cases.xlsx (or wherever specified)
# and uses the data there to output the necessary case data in a json file (case_parameters.json)
# for each type of case.

import os, json
import pandas as pd
from pathlib import Path

def _check_null(val) -> float:
    return 0 if pd.isna(val) else val

def _kmph_to_mps(val: float) -> float:
    return round(val / 3.6, 2)

def _insert(s: str, val: str, index: int) -> str:
    return s[:index] + val + s[index:]

# returns parameters
def gen_single_params(row) -> dict[str, float]:
    # depending on the scenario, the parameters are different.
    # This test data methodology is hard_coded for now.
    params: dict[str, float] = { }
    params["max_speed"] = _kmph_to_mps(_check_null(row.edr_impact_speed_kmph))

    if row.scenario == "cut_in": # TODO. The parameters here are not easily dependent on the case.
        params["relative sp"] = 2 # adjust
        params["dis"] = 10        # adjust
        params["ratio"] = 1       # adjust
    elif row.scenario == "car_following":
        params["sp"] = _kmph_to_mps(row.edr_impact_speed_kmph) # use impact speed
        params["acc"] = 3         # adjust
        params["dec"] = -4        # adjust
    elif row.scenario == "lane_departure_same": # TODO. Similar to cut_in
        params["relative sp"] = 2 # adjust
        params["dis"] = 5         # adjust
        params["ratio"] = 0.7     # adjust
    elif row.scenario == "lane_departure_opposite":
        params["relative sp"] = _kmph_to_mps(_check_null(row.road_speed_limit_kmph)) + _kmph_to_mps(_check_null(row.edr_impact_speed_kmph))
        params["dis"] = 40        # adjust
        params["ratio"] = 1       # adjust
    elif row.scenario == "left_turn_straight":
        params["dis"] = 20        # adjust
        params["sp"] = 10         # adjust
    elif row.scenario == "left_turn_turn":
        params["dis"] = 5         # adjust
        params["sp"] = _kmph_to_mps(row.road_speed_limit_kmph)
    elif row.scenario == "right_turn_straight":
        params["dis"] = 20        # adjust
        params["sp"] = 10         # adjust
    elif row.scenario == "right_turn_turn":
        params["dis"] = 5         # adjust
        params["sp"] = _kmph_to_mps(row.road_speed_limit_kmph)
    elif row.scenario == "vehicle_encroachment":
        params["dis"] = 5         # adjust
        params["angle"] = 90      # adjust
    else:
        print(f"[WARNING] {row.scenario} scenarios are currently not simulated (case {row.cirenid})")
    
    return params


# iterates through cases in master_cases_file
# and outputs parameter values based on prior master_case data
def gen_case_parameters(folder_out: Path, output: Path, master_cases_file: Path, dlt_path: Path) -> None:
    os.makedirs(folder_out, exist_ok=True)

    data = []

    # iterate through each case in master_cases
    master = pd.read_excel(master_cases_file)
    for row in master.itertuples():
        # get metadata for each row
        row_dict: dict = { "cirenid": row.cirenid, "type": row.scenario }
        row_dict["parameters"] = gen_single_params(row)
        
        if len(row_dict["parameters"]) > 1: # don't add if scenario is not supported
            data.append(row_dict)

    # output to file
    with open(output, "w") as file:
        data = json.dumps(data)
        
        # add newlines where appropriate
        data = _insert(data, "\n", 1)
        data = _insert(data, "\n", -1)

        # format json file to look nicer by adding tabs/newlines where appropriate
        curly_count = 0
        result = data
        i = 0
        for char in data:
            if char == "}": curly_count -= 1
            if curly_count == 0:
                if char == "{":
                    result = _insert(result, "\t", i)
                    i += 1
                elif char == "}":
                    result = _insert(result, "\n", i + 2)
                    i += 1
            
            i += 1
            if char == "{": curly_count += 1

        file.write(result)
    
    # format file (O(n))

def main():
    gen_case_parameters(
        "./pipeline/outputs"
        "./pipeline/outputs/case_parameters.json", 
        "./ciren_database/master_cases.xlsx", 
        "~/lab/Behavioral-Safety-Assessment/Driver-Licensing-Test"
    )


if __name__ == "__main__":
    main()
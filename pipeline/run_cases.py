# make sure to delete record.csv before each run to check properly if a collision has occured

import os, json, subprocess
import pandas as pd
from pathlib import Path

import pipeline.edit_speed as edit_speed
import pipeline.process_csv as process_csv

def run_cases(params_json: Path, master_cases_file: Path, dlt_path: Path, verbose: bool) -> pd.DataFrame:
    delta_v_frames: list = []
    skipped: list[int] = [] # list of the cirenid of skipped cases

    # load parameters json file
    with open(params_json, "r") as file:
        data = json.load(file)

    # load master_cases file
    master_df = pd.read_excel(master_cases_file)
    master_df.set_index("cirenid", inplace=True)

    for case in data:
        if verbose: print(f" ---- Running case {case["cirenid"]} ---- ")

        # open parameters file in DLT
        if verbose: print(" - Loading parameters file...")
        params_file_path = f"{dlt_path}/output/Autoware.Universe/case/{case["type"]}/{case["type"]}.json"
        try:
            with open(params_file_path, "r") as file:
                param_file = json.load(file)
        except FileNotFoundError:
            print(f"{params_file_path} not found for case {case["cirenid"]}. Skipping.")
            skipped.append(case["cirenid"])
            continue

        # set max speed using edit_speed.py
        if verbose: print(" - Setting max speed...")
        max_speed = case["parameters"]["max_speed"] # get max speed
        case["parameters"].pop("max_speed") # does not need to set it in the case json below
        edit_speed.main(f"{dlt_path}/env/route/Autoware.Universe/{case["type"]}/map", max_speed)
        
        # set parameters in the DLT file
        if verbose: print(" - Setting parameters file...")
        for key, val in case["parameters"]:
            param_file["low"][0][key] = val
        
        # delete record.csv so we can see if a crash has occurred properly
        if verbose: print(" - Deleting record.csv...")
        test_path = f"{dlt_path}/output/Autoware.Universe/test_data/test_round_1/{case["type"]}"
        record_path = test_path + "/record.csv"
        os.remove(record_path)

        # simulate the scenario
        if verbose: print(" - Simulating scenario...")
        result = subprocess.run(["python", f"{dlt_path}/DLT.py", "--gui",
                                 "--scenario", case["type"], "--case-num", 0, "--round-num", 1])
        # print(result.stdout)

        # find out if a collision has occurred
        if verbose: print(" - Checking collision...")
        collision = False
        record_df = pd.read_csv(record_path)
        for row in record_df.itertuples():
            if row.collision == 1:
                collision = True
                break
        
        if not collision:
            print(f"[WARNING] Case {case["cirenid"]} simulation has not resulted in a collision. Skipping.")
            skipped.append(case["cirenid"])
            continue
        
        # find AV and challenger masses for this case from the master_cases file
        if verbose: print(" - Finding mass of AV and CH...")
        av_mass = master_df.loc[case["cirenid"], "vehicle_curb_weight_kg"]
        ch_mass = master_df.loc[case["cirenid"], "vehicle2_weight"]

        # run delta_v calculations and add to the delta_v_frames dictionary
        if verbose: print(" - Calculating delta_v...")
        result = process_csv.process_csv(test_path, case["cirenid"], 1, True, av_mass, ch_mass)
        delta_v_frames += result

        print(f"- Finished {case["cirenid"]}!")


if __name__ == "__main__":
    run_cases("pipeline/case_parameters.json", "./ciren_database/master_cases.xlsx", "~/lab/Behavioral-Safety-Assessment/Driver-Licensing-Test", True)
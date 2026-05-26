# make sure to delete record.csv before each run to check properly if a collision has occured

import os, json, subprocess, contextlib
import pandas as pd
from pathlib import Path

import edit_speed as edit_speed
import process_csv as process_csv

# runs, simulates, and calculates delta-v given a single case entry from case_parameters file
def run_case(case: dict, master_df: pd.DataFrame, delta_v_frames: list, skipped: list[int], verbose: bool, dlt_path: Path, output_dv_file: Path):
    if verbose: print(f" ---- Running case {case['cirenid']} ---- ")

    # open parameters file in DLT
    if verbose: print(" - Loading parameters file...")
    params_file_path = f"{dlt_path}/output/Autoware.Universe/case/{case['type']}/{case['type']}.json"
    try:
        with open(params_file_path, "r") as file:
            param_file = json.load(file)
    except FileNotFoundError:
        print(f"{params_file_path} not found for case {case['cirenid']}. Skipping.")
        skipped.append(case["cirenid"])
        return

    # set max speed using edit_speed.py
    if verbose: print(" - Setting max speed...")
    max_speed = case["parameters"]["max_speed"] # get max speed
    case["parameters"].pop("max_speed") # does not need to set it in the case json below
    edit_speed.main(f"{dlt_path}/env/route/Autoware.Universe/{case['type']}/map", max_speed)
    
    # set parameters in the DLT file
    if verbose: print(" - Setting parameters file...")
    for key, val in case["parameters"].items():
        param_file["low"][0][key] = val
    
    # output DLT file
    with open(params_file_path, "w") as file:
        json.dump(param_file, file, indent=4)
    
    # delete record.csv so we can see if a crash has occurred properly
    if verbose: print(" - Deleting record.csv...")
    test_path = f"{dlt_path}/output/Autoware.Universe/test_data/test_round_1/{case['type']}"
    record_path = test_path + "/record.csv"

    # ignore if it does not exist already
    with contextlib.suppress(FileNotFoundError):
        os.remove(record_path)

    # simulate the scenario
    if verbose: print(" - Simulating scenario...")
    returncode = 1 # ignore errors and run again if error found
    count = 0

    while returncode != 0 and count <= 10:
        result = subprocess.run(["python", f"{dlt_path}/DLT.py", "--gui",
                                "--scenario", case["type"], "--case-num", "0", "--round-num", "1"])
        returncode = result.returncode
        count += 1
    
    if count > 10:
        print(f"[WARNING] Case {case['cirenid']} ran 10 times unsuccessfully. Skipping.")
        skipped.append(case["cirenid"])
        return

    # find out if a collision has occurred
    if verbose: print(" - Checking collision...")
    collision = False
    record_df = pd.read_csv(record_path)
    for row in record_df.itertuples():
        if row.collision == 1:
            collision = True
            break
    
    if not collision:
        print(f"[WARNING] Case {case['cirenid']} simulation has not resulted in a collision. Skipping.")
        skipped.append(case["cirenid"])
        return
    
    # find AV and challenger masses for this case from the master_cases file
    if verbose: print(" - Finding mass of AV and CH...")
    av_mass = master_df.loc[case["cirenid"], "vehicle_curb_weight_kg"]
    ch_mass = master_df.loc[case["cirenid"], "vehicle2_weight"]

    # run delta_v calculations and add to the delta_v_frames dictionary
    if verbose: print(" - Calculating delta_v...")
    result = process_csv.process_csv(test_path, case["cirenid"], 1, True, av_mass, ch_mass)
    delta_v_frames += result

    print(f"- Finished case {case['cirenid']}!\n\n")

    # save to csv
    results_df = pd.DataFrame(delta_v_frames)
    results_df.to_csv(output_dv_file, index=False)


def run_all(params_json: Path, master_cases_file: Path, verbose: bool, dlt_path: Path, output_dv_file: Path) -> list:
    delta_v_frames: list = []
    skipped: list[int] = [] # list of the cirenid of skipped cases

    # load parameters json file
    with open(params_json, "r") as file:
        data = json.load(file)

    # load master_cases file
    master_df = pd.read_excel(master_cases_file)
    master_df.set_index("cirenid", inplace=True)

    # run all cases
    for case in data:
        run_case(case, master_df, delta_v_frames, skipped, verbose, dlt_path, output_dv_file)

    # skipped cases
    print(f" - SKIPPED CASES: {skipped}")

    return delta_v_frames


def main():
    run_all("pipeline/outputs/case_parameters.json", "./ciren_database/master_cases.xlsx", True, "/home/mzjia/lab/Behavioral-Safety-Assessment/Driver-Licensing-Test", "pipeline/outputs/delta_v_results.csv")


if __name__ == "__main__":
    main()
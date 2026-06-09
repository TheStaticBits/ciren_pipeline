# make sure to delete record.csv before each run to check properly if a collision has occured

import os, rclpy, json, subprocess, atexit, contextlib, asyncio, time
import pandas as pd
from pathlib import Path

import pipeline.parts.edit_speed as edit_speed
import pipeline.parts.gen_delta_v as gen_delta_v
import pipeline.parts.gen_injury_risks as injury_risk
from pipeline.parts.autoware_ros_client import AutowareROSClient
from geometry_msgs.msg import PoseWithCovarianceStamped, PoseStamped

DLT_PATH = Path("/home/mzjia/lab/Behavioral-Safety-Assessment/Driver-Licensing-Test")

# av_locations.json information:
# These numbers were taken from MCity's autoware repo,
# from src/mcity/mcity_abc/src/*.cpp files.
# o means orientation, g means goal

# runs, simulates, and calculates delta-v given a single case entry from case_parameters file
async def run_case(
    case: dict, autoware: AutowareROSClient,
    master_df: pd.DataFrame, av_locs: dict,
    delta_v_frames: list, skipped: list[int],
    verbose: bool, dlt_path: Path, output_dv_file: Path
):
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

    if verbose: print(" - Setting Autoware parameters...")
    param = av_locs[case['type']]
    pos = PoseWithCovarianceStamped()
    pos.pose.pose.position.x = float(param["x"])
    pos.pose.pose.position.y = float(param["y"])
    pos.pose.pose.orientation.x = float(param["o_x"])
    pos.pose.pose.orientation.y = float(param["o_y"])
    pos.pose.pose.orientation.z = float(param["o_z"])
    pos.pose.pose.orientation.w = float(param["o_w"])

    goal = PoseStamped()
    goal.pose.position.x = float(param["g_x"])
    goal.pose.position.y = float(param["g_y"])
    goal.pose.orientation.x = float(param["g_o_x"])
    goal.pose.orientation.y = float(param["g_o_y"])
    goal.pose.orientation.z = float(param["g_o_z"])
    goal.pose.orientation.w = float(param["g_o_w"])

    # set pos and goal
    autoware.pub_pos(pos)
    time.sleep(5)
    autoware.pub_goal(goal)
    # await autoware.set_auto_start(True)
    time.sleep(1000)
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
    
    if verbose: print(" - Disabling Autoware...")
    await autoware.set_auto_start(False)

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
    ch_mass = master_df.loc[case["cirenid"], "challenger_curb_weight_kg"]

    # run delta_v calculations and add to the delta_v_frames dictionary
    if verbose: print(" - Calculating delta_v...")
    result = gen_delta_v.process_csv(test_path, case["cirenid"], 1, True, av_mass, ch_mass)
    delta_v_frames += result

    print(f"- Finished case {case['cirenid']}!\n\n")

    # save to csv
    results_df = pd.DataFrame(delta_v_frames)
    results_df.to_csv(output_dv_file, index=False)


def run_mcity_cosim():
    cmd = ["conda", "deactivate", "&&", "ros2", "launch", "mcity_abc", "mcity_abc.launch.py"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    def kill():
        process.terminate()
        process.wait()
    
    atexit.register(kill)


async def run_all(verbose: bool, params_json: Path, av_locs_json: Path, master_cases_file: Path, dlt_path: Path, output_dv_file: Path, risk_model_file: Path, output_injury_file: Path):
    delta_v_frames: list = []
    skipped: list[int] = [] # list of the cirenid of skipped cases

    # load parameters json file
    with open(params_json, "r") as file:
        data = json.load(file)
    
    # load AV positions json file:
    with open(av_locs_json, "r") as file:
        av_locs = json.load(file)

    # load master_cases file
    master_df = pd.read_excel(master_cases_file)
    master_df.set_index("cirenid", inplace=True)

    # load autoware client
    autoware = AutowareROSClient()
    await autoware.set_autoware_control()
    run_mcity_cosim()

    # run all cases
    for case in data:
        await run_case(case, autoware, master_df, av_locs, delta_v_frames, skipped, verbose, dlt_path, output_dv_file)

    # Print skipped cases
    print(f" - SKIPPED CASES:\n{skipped}\n")

    print(f" ---- Running injury risk calculations ---- ")
    injury_risk.main(output_dv_file, master_cases_file, risk_model_file, output_injury_file)


async def main():
    await run_all(
        verbose=True,
        params_json="pipeline/outputs/case_parameters.json",
        av_locs_json="pipeline/parts/av_locations.jsonc",
        master_cases_file="./ciren_database/master_cases.xlsx",
        dlt_path=DLT_PATH,
        output_dv_file="pipeline/outputs/delta_v_results.csv",
        risk_model_file="ciren/CISS_injury_models_20210415.xlsx",
        output_injury_file="pipeline/outputs/sim_injury_risks.csv"
    )


if __name__ == "__main__":
    rclpy.init()
    asyncio.run(main())
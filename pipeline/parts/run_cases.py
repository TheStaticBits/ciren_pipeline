# make sure to delete record.csv before each run to check properly if a collision has occured

import os, rclpy, json, subprocess, atexit, contextlib, asyncio, time, signal
import pandas as pd
from pathlib import Path

import pipeline.parts.gen_delta_v as gen_delta_v
import pipeline.parts.gen_injury_risks as injury_risk
from pipeline.parts.autoware_ros_client import AutowareROSClient
from geometry_msgs.msg import PoseWithCovarianceStamped, PoseStamped

DLT_PATH = Path("/home/mzjia/lab/Behavioral-Safety-Assessment/Driver-Licensing-Test")
DLT_CASE_TIMEOUT_SEC = 180.0
DLT_MAX_ATTEMPTS = 10

# av_locations.json information:
# These numbers were taken from MCity's autoware repo,
# from src/mcity/mcity_abc/src/*.cpp files.
# o means orientation, g means goal


def get_pos_and_goal(av_locs, scenario_type: str) -> tuple:
    param = av_locs[scenario_type]
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

    return pos, goal


# returns success status
async def set_pos(autoware, pos: PoseWithCovarianceStamped) -> bool:
    localization_deadline = time.monotonic() + 30.0
    while time.monotonic() < localization_deadline:
        autoware.pub_pos(pos)
        localization_initialized = await autoware.wait_for_localization_initialized(timeout_sec=1.0)
        pose_is_near_target = await autoware.wait_for_pose_near(pos, timeout_sec=1.0)
        if localization_initialized and pose_is_near_target:
            return True
    return False


async def set_goal(autoware, goal: PoseStamped, cirenid):
    route_response = None
    for route_attempt in range(1, 4):
        try:
            route_response = await autoware.set_goal(goal)
        except (RuntimeError, TimeoutError) as exc:
            print(f"[WARNING] Case {cirenid} route setup attempt {route_attempt} failed: {exc}.")
        else:
            if route_response.status.success:
                break

            print(
                f"[WARNING] Case {cirenid} route setup attempt {route_attempt} "
                f"was rejected: {route_response.status.message}."
            )

        await asyncio.sleep(1.0)
    return route_response


def record_has_collision(record_path: Path) -> bool:
    try:
        record_df = pd.read_csv(record_path)
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError):
        return False

    if "collision" not in record_df:
        return False

    return bool((record_df["collision"] == 1).any())


def stop_process(process: subprocess.Popen, timeout_sec: float = 10.0):
    if process.poll() is not None:
        return

    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return

    try:
        process.wait(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        process.wait()


async def stop_autoware_driving(autoware: AutowareROSClient):
    try:
        await autoware.set_auto_start(False)
    except Exception as exc:
        print(f"[WARNING] Failed to stop Autoware driving: {exc}")
        return

    stopped = await autoware.wait_for_vehicle_stop()
    if not stopped:
        print("[WARNING] Timed out waiting for AV to come to a full stop.")


async def run_dlt_until_collision_or_timeout(
    case: dict,
    autoware: AutowareROSClient,
    dlt_path: Path,
    record_path: Path,
    timeout_sec: float = DLT_CASE_TIMEOUT_SEC,
) -> tuple[bool, int | None]:
    cmd = [
        "python",
        f"{dlt_path}/DLT.py",
        "--gui",
        "--scenario-folder",
        case["type"],
        "--case-num",
        "0",
        "--round-num",
        "1",
    ]
    process = subprocess.Popen(
        cmd,
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    deadline = time.monotonic() + timeout_sec

    try:
        await asyncio.sleep(2.0)
        await autoware.set_auto_start(True)

        while time.monotonic() < deadline:
            if record_has_collision(record_path):
                return True, process.poll()

            returncode = process.poll()
            if returncode is not None:
                return record_has_collision(record_path), returncode

            await asyncio.sleep(1.0)

        return record_has_collision(record_path), None
    finally:
        await stop_autoware_driving(autoware)
        stop_process(process)

# runs, simulates, and calculates delta-v given a single case entry from case_parameters file
async def run_case(
    case: dict, autoware: AutowareROSClient,
    master_df: pd.DataFrame, av_locs: dict,
    delta_v_frames: list, skipped: list[int],
    verbose: bool, dlt_path: Path, output_dv_file: Path
):
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

    # set max speed in Autoware
    if verbose: print(" - Setting max speed...")
    max_speed = case["parameters"]["max_speed"] # max_speed is already in m/s
    autoware.set_max_velocity(max_speed)
    
    # set parameters in the DLT file
    if verbose: print(" - Setting parameters file...")
    # every element except max_speed, to set in the parameters file
    for key, val in case["parameters"].items():
        if key != "max_speed":
            param_file["low"][0][key] = val
    
    # output DLT file
    with open(params_file_path, "w") as file:
        json.dump(param_file, file, indent=4)
    
    # delete record.csv so we can see if a crash has occurred properly
    if verbose: print(" - Deleting record.csv...")
    test_path = f"{dlt_path}/output/Autoware.Universe/test_data/test_round_1/{case['type']}"
    record_path = Path(test_path) / "record.csv"

    # ignore if it does not exist already
    with contextlib.suppress(FileNotFoundError):
        os.remove(record_path)

    if verbose: print(" - Setting Autoware parameters...")
    init_pos, goal = get_pos_and_goal(av_locs, case['type'])

    # set pos and goal
    pose_set = await set_pos(autoware, init_pos)
    if not pose_set:
        print(f"[WARNING] Case {case['cirenid']} initial pose did not update. Skipping.")
        skipped.append(case["cirenid"])
        return

    route_response = await set_goal(autoware, goal, case['cirenid'])
    if route_response is None:
        print(f"[WARNING] Case {case['cirenid']} route setup failed. Skipping.")
        skipped.append(case["cirenid"])
        return

    if not route_response.status.success:
        print(f"[WARNING] Case {case['cirenid']} route was rejected: {route_response.status.message}. Skipping.")
        skipped.append(case["cirenid"])
        return

    if not await autoware.wait_for_autonomous_available():
        print(f"[WARNING] Case {case['cirenid']} autonomous mode did not become available. Skipping.")
        skipped.append(case["cirenid"])
        return

    # simulate the scenario
    if verbose: print(" - Simulating scenario...")
    collision = False
    for attempt in range(1, DLT_MAX_ATTEMPTS + 1):
        with contextlib.suppress(FileNotFoundError):
            os.remove(record_path)

        if verbose: print(f" - Starting DLT attempt {attempt}/{DLT_MAX_ATTEMPTS}...")
        try:
            collision, returncode = await run_dlt_until_collision_or_timeout(
                case,
                autoware,
                dlt_path,
                record_path,
            )
        except Exception as exc:
            print(f"[WARNING] Case {case['cirenid']} simulation attempt failed: {exc}. Skipping.")
            skipped.append(case["cirenid"])
            return

        if collision:
            break

        if returncode is None:
            print(
                f"[WARNING] Case {case['cirenid']} did not collide within "
                f"{DLT_CASE_TIMEOUT_SEC:.0f}s. Skipping."
            )
            skipped.append(case["cirenid"])
            return

        if returncode == 0:
            print(f"[WARNING] Case {case['cirenid']} finished without a collision. Skipping.")
            skipped.append(case["cirenid"])
            return

        print(
            f"[WARNING] Case {case['cirenid']} DLT attempt {attempt} failed "
            f"with return code {returncode}."
        )
        await set_pos(autoware, init_pos)

        
    
    if not collision:
        print(f"[WARNING] Case {case['cirenid']} ran {DLT_MAX_ATTEMPTS} times unsuccessfully. Skipping.")
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
    launch_file = Path(__file__).with_name("autoware_bg_nodes.launch.py")
    cmd = ["ros2", "launch", str(launch_file)]
    process = subprocess.Popen(cmd)
    
    def kill():
        if process.poll() is not None:
            return

        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    
    atexit.register(kill)
    return process


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
    for index, case in enumerate(data, start=1):
        print(f"\n\n ---- Case {index}/{len(data)}: {case['cirenid']} ({case['type']}) ---- ")
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

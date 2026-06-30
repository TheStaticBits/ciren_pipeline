# This file reads in cases fromm master_cases.xlsx (or wherever specified)
# and uses the data there to output the necessary case data in a json file (case_parameters.json)
# for each type of case.

import os, json
import pandas as pd
from pathlib import Path

# CIREN export placeholder values that mean unknown/not reported, not real measurements.
INVALID_NUMERIC_CODES = {888, 997, 998, 999}

# DLT scenario BV speed limits copied from each scenario's config.yaml.
SPEED_BOUNDS_MPS = {
    "car_following": (2.0, 8.3),
    "left_turn_straight": (3.0, 8.0),
    "left_turn_turn": (1.0, 10.0),
    "right_turn_straight": (1.0, 6.0),
    "right_turn_turn": (1.0, 10.0),
}
BOUND_SPEED = True

# DLT scenario distance/lateral-offset limits copied from each scenario's config.yaml.
DISTANCE_BOUNDS_M = {
    "cut_in": (1.0, 25.0),
    "lane_departure_same": (1.0, 25.0),
    "lane_departure_opposite": (20.0, 70.0),
    "left_turn_straight": (15.0, 50.0),
    "left_turn_turn": (25.0, 60.0),
    "right_turn_straight": (5.0, 30.0),
    "right_turn_turn": (5.0, 30.0),
    "vehicle_encroachment": (-3.8, 3.8),
}

# Treat blank spreadsheet cells as zero for legacy callers that still need a float.
def _check_null(val) -> float:
    return 0 if pd.isna(val) else val

# Convert km/h values from CIREN/EDR fields to m/s for DLT parameters.
def _kmph_to_mps(val: float) -> float:
    return round(val / 3.6, 2)

# Safely read a named attribute from a pandas itertuples() row.
def _row_val(row, name: str):
    return getattr(row, name, None)

# Return a usable numeric value, rejecting NaN and CIREN unknown/not-reported codes.
def _valid_number(val, allow_zero: bool = True):
    try:
        if pd.isna(val):
            return None
    except Exception:
        pass
    try:
        num = float(val)
    except (TypeError, ValueError):
        return None
    if int(num) in INVALID_NUMERIC_CODES:
        return None
    if not allow_zero and num <= 0:
        return None
    return num

# Return the first usable numeric value from a prioritized list of row fields.
def _first_number(row, names: list[str], allow_zero: bool = True):
    for name in names:
        val = _valid_number(_row_val(row, name), allow_zero=allow_zero)
        if val is not None:
            return val
    return None

# Keep a generated parameter inside the DLT scenario's modeled range.
def _clamp(val: float, lower: float, upper: float) -> float:
    return min(max(val, lower), upper)

# Round emitted JSON parameter values to two decimals for readability.
def _round_param(val: float) -> float:
    return round(float(val), 2)

# Read the first available km/h field, convert it to m/s, and optionally clamp it.
def _kmph_field_to_mps(row, names: list[str], lower: float | None = None, upper: float | None = None):
    val = _first_number(row, names, allow_zero=False)
    if val is None:
        return None
    mps = val / 3.6
    if lower is not None and upper is not None:
        mps = _clamp(mps, lower, upper)
    return _round_param(mps)

# Choose the AV/max-speed cap from subject-vehicle EDR speed, falling back to road speed.
def _case_vehicle_speed_mps(row) -> float:
    speed = _kmph_field_to_mps(
        row,
        ["edr_impact_speed_kmph", "edr_initial_speed_kmph", "road_speed_limit_kmph"],
        lower=1.0,
        upper=35.0,
    )
    return speed if speed is not None else 8.3

# Choose the challenger/BV speed from challenger data first, then subject/road fallbacks.
def _challenger_speed_mps(row, scenario: str = None) -> float:
    if scenario and BOUND_SPEED:
        lower, upper = SPEED_BOUNDS_MPS[scenario]
    else:
        lower = None
        upper = None

    speed = _kmph_field_to_mps(
        row,
        [
            "challenger_edr_initial_speed_kmph",
            "challenger_edr_impact_speed_kmph",
            "challenger_road_speed_limit_kmph",
            "road_speed_limit_kmph",
            "edr_impact_speed_kmph",
            "edr_initial_speed_kmph",
        ],
        lower=lower,
        upper=upper,
    )
    return speed if speed is not None else _round_param((lower + upper) / 2)

# Estimate crash severity from delta-v and crush metrics, normalized to a 0..1 score.
def _severity_score(row) -> float:
    components: list[float] = []
    delta_v = _first_number(
        row,
        ["edr_total_delta_v_kmph", "gv_delta_v_total_kmph", "gv_delta_v_best_estimate_kmph"],
        allow_zero=False,
    )
    if delta_v is not None:
        components.append(_clamp(delta_v / 80.0, 0.0, 1.0))

    cmax = _first_number(row, ["primary_cmax_cm"], allow_zero=False)
    if cmax is not None:
        components.append(_clamp(cmax / 80.0, 0.0, 1.0))

    crush_depth = _first_number(row, ["primary_crush_depth_cm"], allow_zero=False)
    if crush_depth is not None:
        components.append(_clamp(crush_depth / 80.0, 0.0, 1.0))

    direct_crush = _first_number(row, ["primary_direct_crush_cm"], allow_zero=False)
    if direct_crush is not None:
        components.append(_clamp(direct_crush / 180.0, 0.0, 1.0))

    return max(components) if components else 0.6

# Estimate subject-vehicle speed loss before impact from EDR initial and impact speed.
def _speed_loss_mps(row) -> float | None:
    initial = _first_number(row, ["edr_initial_speed_kmph"], allow_zero=False)
    impact = _first_number(row, ["edr_impact_speed_kmph"], allow_zero=True)
    if initial is None or impact is None:
        return None
    return max((initial - impact) / 3.6, 0.0)

# Estimate same-direction closing speed for cut-in/lane-departure cases.
# Do not upper-cap it: real crash closing speeds can exceed DLT's generated range.
def _same_direction_relative_speed(row) -> float:
    case_speed = _kmph_field_to_mps(row, ["edr_initial_speed_kmph", "edr_impact_speed_kmph"])
    challenger_speed = _challenger_speed_mps(row)

    if case_speed is not None and challenger_speed is not None:
        rel = abs(case_speed - challenger_speed)
    else:
        loss = _speed_loss_mps(row)
        rel = loss if loss is not None else 0.8 + 1.7 * _severity_score(row)
    return _round_param(max(rel, 0.1))

# Estimate opposite-direction closing speed for head-on lane-departure cases.
# Do not upper-cap it: high-speed head-on crashes should retain their real closing speed.
def _opposite_direction_relative_speed(row) -> float:
    case_speed = _kmph_field_to_mps(row, ["edr_impact_speed_kmph", "edr_initial_speed_kmph", "road_speed_limit_kmph"])
    challenger_speed = _challenger_speed_mps(row)

    if case_speed is not None and challenger_speed is not None:
        rel = case_speed + challenger_speed
    else:
        # map to a range based on severity score, from 10 to 40
        rel = 10 + (30 * _severity_score(row))
    return _round_param(max(rel, 0.1))

# Map higher-severity crashes to shorter initial gaps while staying within DLT bounds.
def _distance_from_severity(row, scenario: str) -> float:
    lower, upper = DISTANCE_BOUNDS_M[scenario]
    severity = _severity_score(row)
    return _round_param(lower + severity * (upper - lower))

# Estimate lateral lane-change ratio from steering and severity within scenario limits.
def _lane_change_ratio(row, lower: float, upper: float, default: float) -> float:
    steering = _first_number(row, ["edr_steering_at_impact_deg"], allow_zero=True)
    if steering is None:
        steer_component = default
    else:
        # normalize to a range from 0 to 1
        steering = steering % 360
        steer_component = min(steering, 360 - steering) / 180.0
    
    # based 70% on severity score, and 30% on the steering component
    severity = _severity_score(row)
    ratio = lower + (upper - lower) * _clamp((severity * 0.7) + (steer_component * 0.3), 0.0, 1.0)
    return _round_param(_clamp(ratio, lower, upper))

# Pick a car-following acceleration target from severity within DLT's feasible range.
def _car_following_acc(row) -> float:
    severity = _severity_score(row)
    return _round_param(_clamp(1.5 + 1.37 * severity, 0.5, 2.87))

# Pick a car-following deceleration target from EDR acceleration, braking, or severity.
def _car_following_dec(row) -> float:
    accel = _first_number(row, ["challenger_edr_preimpact_accel_mps2"], allow_zero=True)
    severity = _severity_score(row)
    if accel is not None and accel < 0:
        dec = accel
    else:
        dec = -(2.5 + 4.0 * severity)
    
    brake_applied = _valid_number(_row_val(row, "edr_brake_applied"), allow_zero=True)
    if brake_applied is not None and brake_applied > 0:
        dec = min(dec, -3.5)
    return _round_param(_clamp(dec, -7.06, -1.0))

# Choose vehicle-encroachment heading from PDOF, falling back to impact clock.
def _encroachment_angle(row) -> float:
    pdof = _first_number(row, ["primary_pdof_deg"], allow_zero=True)
    if pdof is not None:
        return _round_param(pdof % 360)
    clock = _first_number(row, ["primary_impact_clock"], allow_zero=True)
    if clock is not None and 1 <= clock <= 12:
        return _round_param((clock % 12) * 30)
    return 90.0

# Choose vehicle-encroachment lateral offset from impact clock side information.
def _encroachment_distance(row) -> float:
    clock = _first_number(row, ["primary_impact_clock"], allow_zero=True)
    if clock in {2, 3, 4}:
        return 1.9
    if clock in {8, 9, 10}:
        return -1.9
    return 0.0

# Build the DLT parameter dictionary for one master_cases.xlsx row.
def gen_single_params(row) -> dict[str, float]:
    # depending on the scenario, the parameters are different.
    # Parameters are bounded to the DLT scenario ranges and use crash-export
    # fields when those fields map cleanly to the scenario semantics.
    # Currently unsupported here: VRU, roundabout, and traffic-signal DLT cases.
    params: dict[str, float] = { }
    params["max_speed"] = _case_vehicle_speed_mps(row)

    if row.scenario == "cut_in":
        # Cut-in mainly responds to the trigger gap.
        params["relative sp"] = _same_direction_relative_speed(row)
        params["dis"] = _distance_from_severity(row, row.scenario)
        params["ratio"] = 1 # Ratio does not affect this case.
        params["direction"] = "same"

    elif row.scenario == "car_following":
        # sp is the challenger target speed before braking, acc controls how it
        # reaches that speed, and dec controls the stopping phase.
        params["sp"] = _challenger_speed_mps(row, row.scenario)
        params["acc"] = _car_following_acc(row)
        params["dec"] = _car_following_dec(row)

    elif row.scenario == "lane_departure_same":
        # Higher relative sp makes the same-direction challenger slower when it
        # starts departing; dis is the trigger gap and ratio is lane intrusion.
        params["relative sp"] = _same_direction_relative_speed(row)
        params["dis"] = _distance_from_severity(row, row.scenario)
        params["ratio"] = 1
        params["direction"] = "same"

    elif row.scenario == "lane_departure_opposite":
        # Opposite-direction relative sp is AV speed plus challenger speed; dis
        # is the trigger gap and ratio is lane intrusion.
        params["relative sp"] = _opposite_direction_relative_speed(row)
        params["dis"] = _distance_from_severity(row, row.scenario)
        params["ratio"] = 1
        params["direction"] = "opposite"

    elif row.scenario == "left_turn_straight":
        # dis is the initial longitudinal timing distance; sp is the BV's
        # constant speed through the simulation.
        params["dis"] = _distance_from_severity(row, row.scenario)
        params["sp"] = _challenger_speed_mps(row, row.scenario)

    elif row.scenario == "left_turn_turn":
        # dis controls how close the AV is to turning when the challenger starts;
        # sp is the challenger speed while crossing the intersection.
        params["dis"] = _distance_from_severity(row, row.scenario)
        params["sp"] = _challenger_speed_mps(row, row.scenario)

    elif row.scenario == "right_turn_straight":
        # dis is how far the AV has traveled when the challenger starts; values
        # too low or high can miss the collision path. sp is challenger speed.
        params["dis"] = _distance_from_severity(row, row.scenario)
        params["sp"] = _challenger_speed_mps(row, row.scenario)

    elif row.scenario == "right_turn_turn":
        # dis is the AV distance from the intersection when the challenger
        # starts; sp is challenger travel speed.
        params["dis"] = _distance_from_severity(row, row.scenario)
        params["sp"] = _challenger_speed_mps(row, row.scenario)

    elif row.scenario == "vehicle_encroachment":
        # dis is the in-lane lateral offset, positive east; angle is positive
        # clockwise.
        params["dis"] = _encroachment_distance(row)
        params["angle"] = _encroachment_angle(row)

    else:
        print(f"[WARNING] {row.scenario} scenarios are currently not simulated (case {row.cirenid})")
    
    return params


# Write JSON as an array with one compact case object per line.
def _write_cases_json(output: Path, data: list[dict]) -> None:
    with open(output, "w") as file:
        file.write("[\n")
        for i, case in enumerate(data):
            comma = "," if i < len(data) - 1 else ""
            file.write(f"\t{json.dumps(case)}{comma}\n")
        file.write("]\n")


# Iterate through master_cases.xlsx rows and write case_parameters.json.
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

    _write_cases_json(output, data)

# Default CLI entrypoint used by the pipeline scripts.
def main():
    gen_case_parameters(
        "./outputs",
        "./outputs/case_parameters.json", 
        "./outputs/master_cases.xlsx", 
        "~/lab/Behavioral-Safety-Assessment/Driver-Licensing-Test"
    )


if __name__ == "__main__":
    main()

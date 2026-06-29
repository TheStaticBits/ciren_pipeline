"""
Create one-row-per-CrashExport master spreadsheet.

Usage:
    python flatten_exports_to_master.py
    python flatten_exports_to_master.py --input CrashExports --output master_cases.xlsx
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


DEFAULT_INPUT = Path(rf"D:\UMich\Senior Year\umtri\clean\ciren_database\CrashExports")  # path to the downloaded xlsx files
DEFAULT_CATEGORIZED = Path(rf"D:\UMich\Senior Year\umtri\clean\ciren_database\ciren_crash_summaries_categorized.xlsx")  # xlsx file containing the categorized cases
DEFAULT_OUTPUT = Path(rf"D:\UMich\Senior Year\umtri\clean\ciren_database\master_cases.xlsx")  # output file from running this script


def _cirenid_from_filename(xlsx_path: Path) -> int | None:
    match = re.match(r"CrashExport-(\d+)-.*\.xlsx$", xlsx_path.name)
    return int(match.group(1)) if match else None


def _safe(v: Any) -> Any:
    if pd.isna(v):
        return None
    return v


def _read_sheet(xlsx: Path, sheet: str) -> pd.DataFrame:
    try:
        return pd.read_excel(xlsx, sheet_name=sheet)
    except Exception:
        return pd.DataFrame()


def _pick(df: pd.DataFrame, col: str, default=None):
    if df.empty or col not in df.columns:
        return default
    non_null = df[col].dropna()
    if non_null.empty:
        return default
    return _safe(non_null.iloc[0])


def _pick_for_veh(df: pd.DataFrame, col: str, vehno) -> Any:
    if df.empty or col not in df.columns:
        return None
    local = df
    if "VEHNO" in local.columns and vehno is not None:
        local = local[local["VEHNO"].astype(str) == str(vehno)]
        if local.empty:
            return None
    return _pick(local, col)


def _row_count(df: pd.DataFrame) -> int:
    return int(len(df)) if not df.empty else 0


def _to_float(x) -> float | None:
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass
    try:
        return float(x)
    except Exception:
        return None


def _pick_series_for_veh(df: pd.DataFrame, vehno, strict: bool = False) -> pd.DataFrame:
    if df.empty:
        return df
    if "VEHNO" in df.columns and vehno is not None:
        local = df[df["VEHNO"].astype(str) == str(vehno)]
        if not local.empty:
            return local
        if strict:
            return df.iloc[0:0]
    return df


def _compute_edr_precrash(edrpre: pd.DataFrame, vehno, prefix: str = "") -> dict[str, Any]:
    local = _pick_series_for_veh(edrpre, vehno, strict=True)
    if local.empty:
        return {
            f"{prefix}edr_initial_speed_kmph": None,
            f"{prefix}edr_impact_speed_kmph": None,
            f"{prefix}edr_brake_applied": None,
            f"{prefix}edr_steering_at_impact_deg": None,
            f"{prefix}edr_preimpact_accel_mps2": None,
        }

    def _series(pcode: int):
        if "PCODE" not in local.columns:
            return []
        rows = local[local["PCODE"].astype(str) == str(pcode)]
        out = []
        for _, r in rows.iterrows():
            t = _to_float(r.get("PTIME"))
            v = _to_float(r.get("PVALUE"))
            if t is not None and v is not None:
                out.append((t, v))
        return sorted(out, key=lambda x: x[0])

    speed_series = _series(1010)
    brake_series = _series(1040)
    steering_series = _series(1080)

    initial_speed = speed_series[0][1] if speed_series else None
    pre_zero = [(t, v) for t, v in speed_series if t <= 0]
    impact_speed = pre_zero[-1][1] if pre_zero else (speed_series[-1][1] if speed_series else None)
    if speed_series and initial_speed is not None and impact_speed is not None:
        first_t = speed_series[0][0]
        impact_t = pre_zero[-1][0] if pre_zero else speed_series[-1][0]
        dt = impact_t - first_t
        avg_accel = round(((impact_speed - initial_speed) / 3.6) / dt, 2) if dt > 0 else None
    else:
        avg_accel = None
    brake_applied = any(v not in (None, 0.0) for t, v in brake_series if t <= 0) if brake_series else None
    steering_at_impact = next((v for t, v in steering_series if t == 0.0), None)

    return {
        f"{prefix}edr_initial_speed_kmph": initial_speed,
        f"{prefix}edr_impact_speed_kmph": impact_speed,
        f"{prefix}edr_brake_applied": brake_applied,
        f"{prefix}edr_steering_at_impact_deg": steering_at_impact,
        f"{prefix}edr_preimpact_accel_mps2": avg_accel,
    }


def _compute_edr_postcrash(edrpost: pd.DataFrame, vehno, prefix: str = "") -> dict[str, Any]:
    local = _pick_series_for_veh(edrpost, vehno, strict=True)
    if local.empty:
        return {
            f"{prefix}edr_max_delta_v_longitudinal_kmph": None,
            f"{prefix}edr_max_delta_v_lateral_kmph": None,
            f"{prefix}edr_total_delta_v_kmph": None,
        }

    def _max_abs_for_pcode(pcode: int) -> float | None:
        if "PCODE" not in local.columns:
            return None
        rows = local[local["PCODE"].astype(str) == str(pcode)]
        vals = [_to_float(v) for v in rows.get("PVALUE", pd.Series([], dtype=float))]
        vals = [abs(v) for v in vals if v is not None]
        return max(vals) if vals else None

    max_long = _max_abs_for_pcode(2010)
    max_lat = _max_abs_for_pcode(2020)

    if max_long is not None and max_lat is not None:
        total = round((max_long**2 + max_lat**2) ** 0.5, 2)
    elif max_long is not None:
        total = round(max_long, 2)
    else:
        total = None

    return {
        f"{prefix}edr_max_delta_v_longitudinal_kmph": round(max_long, 2) if max_long is not None else None,
        f"{prefix}edr_max_delta_v_lateral_kmph": round(max_lat, 2) if max_lat is not None else None,
        f"{prefix}edr_total_delta_v_kmph": total,
    }


def flatten_one_file(xlsx_path: Path) -> dict[str, Any]:
    cirenid = _cirenid_from_filename(xlsx_path)
    cirencase = _read_sheet(xlsx_path, "CIRENCASE")
    crash = _read_sheet(xlsx_path, "CRASH")
    gv = _read_sheet(xlsx_path, "GV")
    cdc = _read_sheet(xlsx_path, "CDC")
    edrsumm = _read_sheet(xlsx_path, "EDRSUMM")
    edrevent = _read_sheet(xlsx_path, "EDREVENT")
    edrpre = _read_sheet(xlsx_path, "EDRPRECRASH")
    edrpost = _read_sheet(xlsx_path, "EDRPOSTCRASH")
    vehspec = _read_sheet(xlsx_path, "VEHSPEC")
    injury = _read_sheet(xlsx_path, "INJURY")

    caseid = _pick(cirencase, "CASEID") or _pick(crash, "CASEID")
    vehno = _pick(cirencase, "VEHNO")
    challenger_vehno = 2 if vehno == 1 else 1 if vehno == 2 else None

    row: dict[str, Any] = {
        "source_file": xlsx_path.name,
        "cirenid": cirenid,
        "caseid": caseid,
        "vehno": vehno,
        "crash_year": _pick(crash, "CRASHYEAR"),
        "crash_month": _pick(crash, "CRASHMONTH"),
        "num_events": _pick(crash, "EVENTS"),
        "num_vehicles": _pick(crash, "VEHICLES"),
        "case_number": _pick(crash, "CASENUMBER"),
        "psu": _pick(crash, "PSU"),
    }

    # Optional auxiliary fields
    row.update(
        {
            "occno": _pick(cirencase, "OCCNO"),
            "caseno": _pick(crash, "CASENO"),
            "casenumber": _pick(crash, "CASENUMBER"),
            "iss": _pick(cirencase, "ISS"),
            "niss": _pick(cirencase, "NISS"),
            "mais": _pick(cirencase, "MAIS"),
            "age_yr": _pick(cirencase, "AGE_YR"),
            "sex": _pick(cirencase, "SEXTEXT") or _pick(cirencase, "SEX"),
            "height": _pick(cirencase, "HEIGHT"),
            "weight": _pick(cirencase, "WEIGHT"),
            "analysis_text": _pick(cirencase, "ANALYSIS"),
        }
    )

    gv_local = _pick_series_for_veh(gv, vehno)
    gv_oppose = _pick_series_for_veh(gv, challenger_vehno, strict=True)
    vs_local = _pick_series_for_veh(vehspec, vehno)

    # Vehicle-centric fields for case vehicle
    curb = _pick(gv_local, "CURBWT")
    curb_f = _to_float(curb)
    curb_oppose = _pick(gv_oppose, "CURBWT")
    curb_oppose_f = _to_float(curb_oppose)
    row.update(
        {
            "vehicle_make": _pick(gv_local, "MAKETEXT") or _pick(gv_local, "MAKE"),
            "vehicle_model": _pick(gv_local, "MODELTEXT") or _pick(gv_local, "MODEL"),
            "vehicle_model_year": _pick(gv_local, "MODELYR"),
            "vehicle_curb_weight_kg": round(curb_f, 1) if curb_f is not None else None,
            "challenger_curb_weight_kg": round(curb_oppose_f, 1) if curb_oppose_f is not None else None,
            "vehicle_wheelbase_cm": _pick(vs_local, "WHEELBASE"),
            "vehicle_track_width_cm": _pick(vs_local, "TRACKWIDTH"),
            "vehicle_overall_length_cm": _pick(vs_local, "OAL"),
            "vehicle_engine_cylinders": _pick(vs_local, "ENG_CYL"),
            "vehicle_engine_displacement_l": _pick(vs_local, "ENG_DISP"),
            "vehicle_damage_plane": _pick(gv_local, "DAMPLANETEXT") or _pick(gv_local, "DAMPLANE"),
            "vehicle_damage_severity": _pick(gv_local, "DAMSEVTEXT") or _pick(gv_local, "DAMSEV"),
            "road_speed_limit_kmph": _pick(gv_local, "SPEEDLIMIT"),
            "challenger_road_speed_limit_kmph": _pick(gv_oppose, "SPEEDLIMIT"),
        }
    )

    # EDR pre/post derived metrics
    row.update(_compute_edr_precrash(edrpre, vehno))
    row.update(_compute_edr_postcrash(edrpost, vehno))
    row.update(_compute_edr_precrash(edrpre, challenger_vehno, "challenger_"))
    row.update(_compute_edr_postcrash(edrpre, challenger_vehno, "challenger_"))

    edrsumm_local = _pick_series_for_veh(edrsumm, vehno, strict=True)
    edrevent_local = _pick_series_for_veh(edrevent, vehno, strict=True)

    row.update(
        {
            "edr_num_events": _pick(edrsumm_local, "NUMEVENTS"),
            "edr_peak_delta_v_long_kmph": _pick(edrevent_local, "MAXDVLONG"),
            "edr_peak_delta_v_lat_kmph": _pick(edrevent_local, "MAXDVLAT"),
            "edr_peak_dv_long_time_ms": _pick(edrevent_local, "MAXDVLONGTIME"),
            "edr_peak_dv_lat_time_ms": _pick(edrevent_local, "MAXDVLATTIME"),
            "edr_ignition_cycles_at_crash": _pick(edrevent_local, "IGCYCRASH"),
            "edr_cdr_tool_version": _pick(edrsumm_local, "CDRVERCOLL"),
        }
    )

    cdc_local = _pick_series_for_veh(cdc, vehno)
    if not cdc_local.empty and "DVRANK" in cdc_local.columns:
        cdc_local = cdc_local.copy()
        cdc_local["_dvrank_num"] = pd.to_numeric(cdc_local["DVRANK"], errors="coerce")
        cdc_local = cdc_local.sort_values("_dvrank_num", na_position="last")

    row.update(
        {
            "primary_pdof_deg": _pick(cdc_local, "PDOF"),
            "primary_impact_clock": _pick(cdc_local, "OCLOCK"),
            "primary_damage_plane": _pick(cdc_local, "CDCPLANE"),
            "primary_object_struck": _pick(cdc_local, "OBJCONTTEXT") or _pick(cdc_local, "OBJCONT"),
            "primary_crush_extent_zones": _pick(cdc_local, "CDCEXTENT"),
            "primary_direct_crush_cm": _pick(cdc_local, "DIRECTL"),
            "primary_crush_depth_cm": _pick(cdc_local, "DIRECTD"),
            "primary_cmax_cm": _pick(cdc_local, "CMAX"),
            "primary_dv_estimate_label": _pick(cdc_local, "DVESTIMATETEXT") or _pick(cdc_local, "DVESTIMATE"),
        }
    )

    row.update(
        {
            "gv_delta_v_best_estimate_kmph": _pick(gv_local, "DVBES"),
            "gv_delta_v_total_kmph": _pick(gv_local, "DVTOTAL"),
            "gv_delta_v_longitudinal_kmph": _pick(gv_local, "DVLONG"),
            "gv_delta_v_lateral_kmph": _pick(gv_local, "DVLAT"),
            "gv_pre_crash_maneuver": _pick(gv_local, "MANEUVERTEXT") or _pick(gv_local, "MANEUVER"),
            "gv_crash_type": _pick(gv_local, "CRASHTYPETEXT") or _pick(gv_local, "CRASHTYPE"),
            "gv_crash_config": _pick(gv_local, "CRASHCONFTEXT") or _pick(gv_local, "CRASHCONF"),
            "gv_road_alignment": _pick(gv_local, "ALIGNMENTTEXT") or _pick(gv_local, "ALIGNMENT"),
            "gv_road_profile": _pick(gv_local, "PROFILETEXT") or _pick(gv_local, "PROFILE"),
            "gv_surface_condition": _pick(gv_local, "SURFCONDTEXT") or _pick(gv_local, "SURFCOND"),
            "gv_light_condition": _pick(gv_local, "LIGHTCONDTEXT") or _pick(gv_local, "LIGHTCOND"),
            "gv_tree_pole_diameter_cm": _pick(gv_local, "TREEPOLE"),
            "gv_num_vehicles": _pick(crash, "VEHICLES"),
            "gv_num_events": _pick(crash, "EVENTS"),
            "challenger_gv_delta_v_best_estimate_kmph": _pick(gv_oppose, "DVBES"),
            "challenger_gv_delta_v_total_kmph": _pick(gv_oppose, "DVTOTAL"),
            "challenger_gv_delta_v_longitudinal_kmph": _pick(gv_oppose, "DVLONG"),
            "challenger_gv_delta_v_lateral_kmph": _pick(gv_oppose, "DVLAT"),
            "challenger_gv_pre_crash_maneuver": _pick(gv_oppose, "MANEUVERTEXT") or _pick(gv_oppose, "MANEUVER"),
            "challenger_gv_crash_type": _pick(gv_oppose, "CRASHTYPETEXT") or _pick(gv_oppose, "CRASHTYPE"),
            "challenger_gv_crash_config": _pick(gv_oppose, "CRASHCONFTEXT") or _pick(gv_oppose, "CRASHCONF"),
        }
    )

    # Include table sizes so many-to-one info isn't silently lost.
    row.update(
        {
            "rows_CIRENCASE": _row_count(cirencase),
            "rows_CRASH": _row_count(crash),
            "rows_GV": _row_count(gv),
            "rows_CDC": _row_count(cdc),
            "rows_INJURY": _row_count(injury),
            "rows_VEHSPEC": _row_count(vehspec),
            "rows_EDRSUMM": _row_count(edrsumm),
            "rows_EDREVENT": _row_count(edrevent),
            "rows_EDRPRECRASH": _row_count(edrpre),
            "rows_EDRPOSTCRASH": _row_count(edrpost),
        }
    )

    return row


def _load_allowed_cases(categorized_file: Path) -> pd.DataFrame:
    if not categorized_file.exists():
        raise FileNotFoundError(f"Categorized file not found: {categorized_file}")

    df = pd.read_excel(categorized_file)
    needed = {"cirenid", "crash_summary", "scenario"}
    if not needed.issubset(df.columns):
        raise ValueError(
            f"{categorized_file} must contain columns: cirenid, crash_summary, scenario"
        )

    out = df[["cirenid", "crash_summary", "scenario"]].copy()
    out["cirenid"] = out["cirenid"].astype(str)
    out = out.drop_duplicates(subset=["cirenid"], keep="first")
    return out


def build_master(
    input_dir: Path,
    output_file: Path,
    categorized_file: Path,
    start_index: int = 0,
    max_files: int | None = None,
    checkpoint_every: int = 25,
    ciren_ids: set[int] = None
) -> tuple[pd.DataFrame, list[int]]:
    xlsx_files = sorted(input_dir.glob("CrashExport-*.xlsx"))
    if not xlsx_files:
        raise FileNotFoundError(f"No CrashExport-*.xlsx files found in {input_dir}")

    xlsx_files = xlsx_files[start_index:]
    if max_files is not None:
        xlsx_files = xlsx_files[:max_files]

    allowed = _load_allowed_cases(categorized_file)
    allowed_lookup = allowed.set_index("cirenid")
    allowed_ids = set(allowed_lookup.index)
    requested_ids = {str(cirenid) for cirenid in ciren_ids} if ciren_ids is not None else None

    i = 0
    rows = []
    successful_ciren_ids: list[int] = []
    for xlsx in xlsx_files:

        cirenid = _cirenid_from_filename(xlsx)
        if cirenid is None:
            print(f"Skipping Case: could not parse CIREN ID from filename")
            continue

        cirenid_str = str(cirenid)
        if requested_ids is not None and cirenid_str not in requested_ids:
            continue
        if cirenid_str not in allowed_ids:
            continue
        
        i += 1
        print(f"[{i}/{len(ciren_ids)}] {xlsx.name}")
        row = flatten_one_file(xlsx)
        successful_ciren_ids.append(cirenid)

        match = allowed_lookup.loc[cirenid_str]
        row["crash_summary"] = match["crash_summary"]
        row["scenario"] = match["scenario"]
        rows.append(row)

        if checkpoint_every > 0 and i % checkpoint_every == 0:
            tmp = output_file.with_name(output_file.stem + "_checkpoint.xlsx")
            pd.DataFrame(rows).to_excel(tmp, index=False)
            print(f"    checkpoint -> {tmp}")

    df = pd.DataFrame(rows)
    df = df.sort_values(["cirenid", "caseid"], na_position="last").reset_index(drop=True)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_file, index=False)
    return (df, successful_ciren_ids)


# returns successful ciren case IDs
def main(input_folder: Path, output_file: Path, input_categorized: Path, start_index: int, max_files: int, checkpoint_every: int, ciren_ids: set[int] = None) -> list[int]:
    df, successful_ids = build_master(
        input_folder,
        output_file,
        categorized_file=input_categorized,
        start_index=start_index,
        max_files=max_files,
        checkpoint_every=checkpoint_every,
        ciren_ids=ciren_ids
    )
    print(f" - Flattened {len(df)} rows to {output_file} masterfile")
    return successful_ids


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flatten CrashExport xlsx files into one-row-per-case master sheet.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Folder containing CrashExport-*.xlsx files")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output xlsx path for master sheet")
    parser.add_argument("--categorized", type=Path, default=DEFAULT_CATEGORIZED, help="Path to ciren_crash_summaries_categorized.xlsx")
    parser.add_argument("--start-index", type=int, default=0, help="Start index in sorted file list (0-based)")
    parser.add_argument("--max-files", type=int, default=None, help="Process at most this many files")
    parser.add_argument("--checkpoint-every", type=int, default=25, help="Write checkpoint workbook every N files")
    args = parser.parse_args()

    main(args.input, args.output, args.categorized, args.start_index, args.max_files, args.checkpoint_every)

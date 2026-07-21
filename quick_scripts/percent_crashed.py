from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASE_PARAMETERS = REPO_ROOT / "outputs/case_parameters.json"
DEFAULT_DELTA_V_RESULTS = REPO_ROOT / "outputs/delta_v_results.csv"
DEFAULT_OUTPUT_CSV = REPO_ROOT / "outputs/percent_crashed_by_type.csv"
DEFAULT_OUTPUT_PLOT = REPO_ROOT / "outputs/percent_crashed_by_type.png"


def _load_case_parameters(path: Path) -> list[dict]:
    with path.open("r") as file:
        cases = json.load(file)

    if not isinstance(cases, list):
        raise ValueError(f"{path} should contain a list of case dictionaries.")

    return cases


def _crashed_ids(delta_v_results: Path, require_delta_v: bool) -> set[int]:
    delta_v = pd.read_csv(delta_v_results)
    if "cirenid" not in delta_v.columns:
        raise ValueError(f"{delta_v_results} must contain a cirenid column.")

    if require_delta_v:
        delta_cols = [
            col
            for col in delta_v.columns
            if "delta_v" in col.lower() or col.lower().endswith("_v_final")
        ]
        if not delta_cols:
            raise ValueError(f"{delta_v_results} does not contain any delta-v columns.")

        has_delta_v = delta_v[delta_cols].apply(
            lambda col: pd.to_numeric(col, errors="coerce")
        ).notna().any(axis=1)
        delta_v = delta_v.loc[has_delta_v]

    ids = pd.to_numeric(delta_v["cirenid"], errors="coerce").dropna().astype(int)
    return set(ids)


def _summarize_by_type(cases: list[dict], crashed: set[int]) -> pd.DataFrame:
    total_by_type: Counter[str] = Counter()
    crashed_by_type: defaultdict[str, int] = defaultdict(int)

    for case in cases:
        crash_type = case.get("type")
        cirenid = case.get("cirenid")
        if crash_type is None or cirenid is None:
            continue

        cirenid = int(cirenid)
        total_by_type[crash_type] += 1
        if cirenid in crashed:
            crashed_by_type[crash_type] += 1

    rows = []
    for crash_type, total in total_by_type.items():
        crashed_count = crashed_by_type[crash_type]
        rows.append(
            {
                "crash_type": crash_type,
                "simulated_count": total,
                "crashed_count": crashed_count,
                "percent_crashed": (crashed_count / total) * 100,
            }
        )

    return pd.DataFrame(rows).sort_values("percent_crashed", ascending=False)


def _plot(summary: pd.DataFrame, output_plot: Path) -> None:
    fig_width = max(9, len(summary) * 1.1)
    fig, ax = plt.subplots(figsize=(fig_width, 6))

    bars = ax.bar(summary["crash_type"], summary["percent_crashed"], color="#4C78A8")
    ax.set_ylim(0, 100)
    ax.set_ylabel("Percent that Crashed in Simulation")
    ax.set_xlabel("Crash type")
    ax.set_title("Crash Simulations That Resulted in a Crash by Type")
    ax.tick_params(axis="x", rotation=35)

    for bar, row in zip(bars, summary.itertuples(index=False)):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,
            f"{row.percent_crashed:.1f}%\n{row.crashed_count}/{row.simulated_count}",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    fig.tight_layout()
    fig.savefig(output_plot, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Graph the percent of each crash type in case_parameters.json that "
            "also appears in delta_v_results.csv."
        )
    )
    parser.add_argument("--case-parameters", type=Path, default=DEFAULT_CASE_PARAMETERS)
    parser.add_argument("--delta-v-results", type=Path, default=DEFAULT_DELTA_V_RESULTS)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--output-plot", type=Path, default=DEFAULT_OUTPUT_PLOT)
    parser.add_argument(
        "--require-delta-v",
        action="store_true",
        help="Only count delta_v_results.csv rows that have at least one numeric delta-v value.",
    )
    args = parser.parse_args()

    cases = _load_case_parameters(args.case_parameters)
    crashed = _crashed_ids(args.delta_v_results, args.require_delta_v)
    summary = _summarize_by_type(cases, crashed)

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.output_plot.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.output_csv, index=False)
    _plot(summary, args.output_plot)

    print(summary.to_string(index=False, formatters={"percent_crashed": "{:.1f}".format}))
    print(f"\nWrote {args.output_csv}")
    print(f"Wrote {args.output_plot}")


if __name__ == "__main__":
    main()

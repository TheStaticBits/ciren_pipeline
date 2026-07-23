"""Compare injury risks for cases shared by two result files.

The generated figure has one panel for each injury-risk measure.  Each panel
overlays the mean base and comparison risks for every precrash scenario and
shows the corresponding percentage reduction on a secondary axis.  The
horizontal dashed line is the overall reduction across all matched cases.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]

# Change these defaults here, or pass --base and --compare on the command line.
INJURY_RISK_BASE = REPO_ROOT / "outputs/real_injury_risks.csv"
INJURY_RISK_COMPARE = REPO_ROOT / "outputs/sim_injury_risks_1.0.csv"

OUTPUT_PLOT = REPO_ROOT / "outputs/visualizations/injury_risk_comparison.png"
OUTPUT_SUMMARY = REPO_ROOT / "outputs/visualizations/injury_risk_comparison.csv"

CASE_ID_COLUMN = "cirenid"
SCENARIO_COLUMN = "category"
RISK_COLUMNS = {
    "Head_Risk": "Head",
    "Chest_Risk": "Chest",
    "LowerExtremity_Risk": "Lower extremity",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare injury risks by precrash scenario for cases present in "
            "both input CSV files."
        )
    )
    parser.add_argument(
        "--base",
        type=Path,
        default=INJURY_RISK_BASE,
        help=f"Base injury-risk CSV (default: {INJURY_RISK_BASE})",
    )
    parser.add_argument(
        "--compare",
        type=Path,
        default=INJURY_RISK_COMPARE,
        help=f"Comparison injury-risk CSV (default: {INJURY_RISK_COMPARE})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PLOT,
        help=f"Output chart path (default: {OUTPUT_PLOT})",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=OUTPUT_SUMMARY,
        help=f"Output summary CSV path (default: {OUTPUT_SUMMARY})",
    )
    return parser.parse_args()


def _read_risks(path: Path, name: str) -> pd.DataFrame:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"{name} file does not exist: {path}")

    df = pd.read_csv(path)
    required = {CASE_ID_COLUMN, SCENARIO_COLUMN, *RISK_COLUMNS}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(missing)}")

    if df[CASE_ID_COLUMN].duplicated().any():
        duplicate_ids = (
            df.loc[df[CASE_ID_COLUMN].duplicated(keep=False), CASE_ID_COLUMN]
            .astype(str)
            .unique()
        )
        preview = ", ".join(duplicate_ids[:5])
        raise ValueError(
            f"{path} has duplicate {CASE_ID_COLUMN} values ({preview}); "
            "each case must occur once."
        )

    result = df[[CASE_ID_COLUMN, SCENARIO_COLUMN, *RISK_COLUMNS]].copy()
    for column in RISK_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    return result


def _match_cases(base: pd.DataFrame, compare: pd.DataFrame) -> pd.DataFrame:
    matched = base.merge(
        compare,
        on=CASE_ID_COLUMN,
        how="inner",
        suffixes=("_base", "_compare"),
        validate="one_to_one",
    )
    if matched.empty:
        raise ValueError("The input files do not contain any shared cases.")

    base_scenario = f"{SCENARIO_COLUMN}_base"
    compare_scenario = f"{SCENARIO_COLUMN}_compare"
    scenario_mismatch = (
        matched[base_scenario].fillna("").astype(str)
        != matched[compare_scenario].fillna("").astype(str)
    )
    if scenario_mismatch.any():
        case_ids = matched.loc[scenario_mismatch, CASE_ID_COLUMN].astype(str)
        preview = ", ".join(case_ids.iloc[:5])
        raise ValueError(
            "Matched cases have different precrash scenarios in the two "
            f"files ({preview})."
        )

    matched[SCENARIO_COLUMN] = matched[base_scenario]
    matched = matched.dropna(subset=[SCENARIO_COLUMN])
    if matched.empty:
        raise ValueError("No matched cases have a precrash scenario.")
    return matched


def _reduction_percent(base: pd.Series, compare: pd.Series) -> float:
    """Return the percentage reduction from the mean base risk."""
    valid = base.notna() & compare.notna()
    if not valid.any():
        return float("nan")

    base_mean = base[valid].mean()
    compare_mean = compare[valid].mean()
    if base_mean == 0:
        return float("nan")
    return float((base_mean - compare_mean) / base_mean * 100.0)


def _build_summary(matched: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    scenarios = sorted(matched[SCENARIO_COLUMN].astype(str).unique())

    for scenario in scenarios:
        scenario_rows = matched[
            matched[SCENARIO_COLUMN].astype(str).eq(scenario)
        ]
        row: dict[str, object] = {
            "scenario": scenario,
            "matched_cases": len(scenario_rows),
        }
        for risk_column in RISK_COLUMNS:
            base_column = f"{risk_column}_base"
            compare_column = f"{risk_column}_compare"
            valid = (
                scenario_rows[base_column].notna()
                & scenario_rows[compare_column].notna()
            )
            row[f"{risk_column}_matched_cases"] = int(valid.sum())
            row[f"{risk_column}_base_mean"] = scenario_rows.loc[
                valid, base_column
            ].mean()
            row[f"{risk_column}_compare_mean"] = scenario_rows.loc[
                valid, compare_column
            ].mean()
            row[f"{risk_column}_reduction_percent"] = _reduction_percent(
                scenario_rows[base_column],
                scenario_rows[compare_column],
            )
        rows.append(row)

    return pd.DataFrame(rows)


def _plot(
    matched: pd.DataFrame,
    summary: pd.DataFrame,
    output_path: Path,
) -> dict[str, float]:
    scenario_labels = [
        f"{scenario.replace('_', ' ').title()}\n(n={case_count})"
        for scenario, case_count in zip(
            summary["scenario"], summary["matched_cases"]
        )
    ]
    x = np.arange(len(summary))

    fig, axes = plt.subplots(
        len(RISK_COLUMNS),
        1,
        figsize=(14, 12),
        sharex=True,
        constrained_layout=True,
    )
    axes = np.atleast_1d(axes)
    overall_reductions: dict[str, float] = {}

    for ax, (risk_column, display_name) in zip(axes, RISK_COLUMNS.items()):
        base_mean = summary[f"{risk_column}_base_mean"] * 100.0
        compare_mean = summary[f"{risk_column}_compare_mean"] * 100.0
        scenario_reduction = summary[f"{risk_column}_reduction_percent"]
        overall_reduction = _reduction_percent(
            matched[f"{risk_column}_base"],
            matched[f"{risk_column}_compare"],
        )
        overall_reductions[risk_column] = overall_reduction

        # A narrower comparison bar over the base bar makes both values visible.
        ax.bar(
            x,
            base_mean,
            width=0.72,
            color="#4C78A8",
            alpha=0.55,
            label="Real mean risk",
            zorder=2,
        )
        ax.bar(
            x,
            compare_mean,
            width=0.42,
            color="#F58518",
            alpha=0.90,
            label="ADS mean risk",
            zorder=3,
        )
        ax.set_ylabel(f"{display_name} injury risk (%)")
        ax.set_ylim(bottom=0)
        ax.grid(axis="y", linestyle=":", alpha=0.4, zorder=1)

        reduction_ax = ax.twinx()
        reduction_ax.scatter(
            x,
            scenario_reduction,
            marker="D",
            s=38,
            color="#2A9D8F",
            label="Risk reduction",
            zorder=5,
        )
        if np.isfinite(overall_reduction):
            reduction_ax.axhline(
                overall_reduction,
                color="#B22222",
                linestyle="--",
                linewidth=1.6,
                label=f"Reduction in mean risk: {overall_reduction:.1f}%",
                zorder=4,
            )
        reduction_ax.axhline(0, color="black", linewidth=0.7, alpha=0.5)
        reduction_ax.set_ylabel("Risk reduction (%)")
        # A symmetric log scale keeps near-zero and very large percentage
        # changes readable when a scenario's base risk is extremely small.
        reduction_ax.set_yscale("symlog", linthresh=10)
        reduction_ax.margins(y=0.15)

        for point_x, reduction in zip(x, scenario_reduction):
            if np.isfinite(reduction):
                reduction_ax.annotate(
                    f"{reduction:.1f}%",
                    (point_x, reduction),
                    xytext=(0, 7),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color="#176B60",
                )

        left_handles, left_labels = ax.get_legend_handles_labels()
        right_handles, right_labels = reduction_ax.get_legend_handles_labels()
        ax.legend(
            left_handles + right_handles,
            left_labels + right_labels,
            loc="upper left",
            ncols=2,
            fontsize=8,
        )

    axes[-1].set_xticks(x)
    axes[-1].set_xticklabels(scenario_labels, rotation=25, ha="right")
    axes[-1].set_xlabel("Precrash scenario type")
    axes[0].set_title(
        "Injury Risk Comparison by Precrash Scenario\n"
        f"{len(matched)} cases present in both files",
        fontsize=15,
        pad=14,
    )

    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return overall_reductions


def main() -> None:
    args = _parse_args()
    base = _read_risks(args.base, "Base")
    compare = _read_risks(args.compare, "Comparison")
    matched = _match_cases(base, compare)
    summary = _build_summary(matched)

    summary_path = args.summary.expanduser().resolve()
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(summary_path, index=False)
    overall_reductions = _plot(matched, summary, args.output)

    print(
        f"Compared {len(matched)} shared cases "
        f"({len(base) - len(matched)} base-only, "
        f"{len(compare) - len(matched)} comparison-only)."
    )
    for risk_column, reduction in overall_reductions.items():
        print(f"{RISK_COLUMNS[risk_column]} reduction: {reduction:.2f}%")
    print(f"Wrote {args.output.expanduser().resolve()}")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()

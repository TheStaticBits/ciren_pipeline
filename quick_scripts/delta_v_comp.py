from pathlib import Path
import os
import sys

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


file1 = "outputs/delta_v_results_1.0.csv"
file2 = "outputs/delta_v_results_1.2.csv"

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

import ciren_database.calculate_injury_risks as calc_risk


master_file = "outputs/master_cases.xlsx"
model_file = "ciren_database/CISS_injury_models_20210415.xlsx"
output_csv = "outputs/visualizations/delta_v_injury_risk_comparison.csv"
output_plot = "outputs/visualizations/delta_v_injury_risk_comparison.png"

key_cols = ["cirenid", "case"]
risk_cols = ["Head_Risk", "Chest_Risk", "LowerExtremity_Risk"]


def _path(path: str) -> Path:
    return repo_root / path


def _read_delta_v(path: str) -> pd.DataFrame:
    csv_path = _path(path)
    return pd.read_csv(csv_path)


def _master_row(master_df: pd.DataFrame, cirenid: int) -> pd.Series:
    row = master_df.loc[cirenid].copy()
    if isinstance(row, pd.DataFrame):
        row = row.iloc[0].copy()
    return row


def _risk_rows(delta_v_df: pd.DataFrame, master_df: pd.DataFrame, model) -> pd.DataFrame:
    rows = []

    for _, row in delta_v_df.iterrows():
        cirenid = int(row["cirenid"])
        master_row = _master_row(master_df, cirenid)
        master_row["total_delta_v"] = float(row["2D_delta_v_av"])

        risks = model.calculate_all_risks(master_row)
        rows.append(
            {
                "cirenid": cirenid,
                "case": int(row["case"]),
                "category": master_row["scenario"],
                **{col: risks[col] for col in risk_cols},
            }
        )

    return pd.DataFrame(rows)


def _plot_comparison(comp: pd.DataFrame) -> None:
    labels = [f"{int(row.cirenid)}-{int(row.case)}" for row in comp.itertuples()]
    x = range(len(comp))

    fig, axes = plt.subplots(len(risk_cols), 1, figsize=(12, 9), sharex=True)
    if len(risk_cols) == 1:
        axes = [axes]

    for ax, risk_col in zip(axes, risk_cols):
        diff_col = f"{risk_col}_diff"
        ax.bar(x, comp[diff_col])
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_ylabel(diff_col)

    axes[-1].set_xticks(list(x))
    axes[-1].set_xticklabels(labels, rotation=90)
    axes[-1].set_xlabel("cirenid-case")
    fig.tight_layout()
    fig.savefig(_path(output_plot), dpi=150)
    plt.close(fig)


def main() -> None:
    df1 = _read_delta_v(file1)
    df2 = _read_delta_v(file2)

    common_keys = df1[key_cols].merge(df2[key_cols], on=key_cols)
    df1 = common_keys.merge(df1, on=key_cols)
    df2 = common_keys.merge(df2, on=key_cols)

    master_df = pd.read_excel(_path(master_file))
    master_df.set_index("cirenid", inplace=True)
    master_df["age_yr"] = master_df["age_yr"].apply(calc_risk.parse_numeric)
    master_df["height"] = master_df["height"].apply(calc_risk.parse_numeric)
    master_df["weight"] = master_df["weight"].apply(calc_risk.parse_numeric)
    master_df["bmi"] = master_df.apply(
        lambda row: calc_risk.calculate_bmi(row["height"], row["weight"]),
        axis=1,
    )

    model = calc_risk.InjuryRiskModel(_path(model_file))
    risks1 = _risk_rows(df1, master_df, model)
    risks2 = _risk_rows(df2, master_df, model)

    comp = risks1.merge(risks2, on=key_cols, suffixes=("_file1", "_file2"))
    for risk_col in risk_cols:
        comp[f"{risk_col}_diff"] = comp[f"{risk_col}_file2"] - comp[f"{risk_col}_file1"]

    _path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    _path(output_plot).parent.mkdir(parents=True, exist_ok=True)
    comp.to_csv(_path(output_csv), index=False)
    _plot_comparison(comp)

    print(f"Compared {len(comp)} shared cases.")
    print(f"Wrote {_path(output_csv)}")
    print(f"Wrote {_path(output_plot)}")


if __name__ == "__main__":
    main()

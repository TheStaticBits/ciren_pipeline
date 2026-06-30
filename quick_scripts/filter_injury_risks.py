from pathlib import Path

import pandas as pd


# This script opens outputs/injury_risk_calculations.csv and removes
# cases that are not also present in outputs/sim_injury_risks.csv.

INJURY_RISKS_PATH = Path("outputs/injury_risk_calculations.csv")
SIM_RISKS_PATH = Path("outputs/sim_injury_risks.csv")
CASE_ID_COLUMN = "cirenid"


def _case_ids(df: pd.DataFrame, path: Path) -> set[int]:
    if CASE_ID_COLUMN not in df.columns:
        raise ValueError(f"{path} is missing required column {CASE_ID_COLUMN!r}")
    return set(pd.to_numeric(df[CASE_ID_COLUMN], errors="raise").astype(int))


def main() -> None:
    injury_risks = pd.read_csv(INJURY_RISKS_PATH)
    sim_risks = pd.read_csv(SIM_RISKS_PATH)

    simulated_case_ids = _case_ids(sim_risks, SIM_RISKS_PATH)
    injury_case_ids = pd.to_numeric(
        injury_risks[CASE_ID_COLUMN], errors="raise"
    ).astype(int)

    filtered = injury_risks[injury_case_ids.isin(simulated_case_ids)].copy()
    filtered.to_csv(INJURY_RISKS_PATH, index=False)

    removed_count = len(injury_risks) - len(filtered)
    print(
        f"Kept {len(filtered)} rows in {INJURY_RISKS_PATH}; "
        f"removed {removed_count} rows not present in {SIM_RISKS_PATH}."
    )


if __name__ == "__main__":
    main()

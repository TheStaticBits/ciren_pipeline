import pandas as pd
from pathlib import Path

from ciren.calculate_injury_risks import InjuryRiskModel

def main(delta_v_file: Path, master_file: Path):
    # read in input files
    master_df = pd.read_excel(master_file)
    master_df.set_index("cirenid", inplace=True)
    dv_df = pd.read_csv(delta_v_file)

    # calculate necessary information to plug into InjuryRiskModel


if __name__ == "__main__":
    main("pipeline/outputs/delta_v_results.csv")
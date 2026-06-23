import pandas as pd
from pathlib import Path
import sys
from pathlib import Path

# Add parent directory to path for ciren imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import ciren_database.calculate_injury_risks as calc_risk

def main(delta_v_file: Path, master_file: Path, model_file: Path, output_file: Path) -> None:
    # read in input files
    master_df = pd.read_excel(master_file)
    master_df.set_index("cirenid", inplace=True)
    dv_df = pd.read_csv(delta_v_file)

    # data prep
    master_df['age_yr'] = master_df['age_yr'].apply(calc_risk.parse_numeric)
    master_df['height'] = master_df['height'].apply(calc_risk.parse_numeric)
    master_df['weight'] = master_df['weight'].apply(calc_risk.parse_numeric)
    
    # calculate BMI for each case
    master_df['bmi'] = master_df.apply(
        lambda row: calc_risk.calculate_bmi(row['height'], row['weight']), 
        axis=1
    )

    # create model
    model = calc_risk.InjuryRiskModel(model_file)

    # iterate and run model on each row
    # inputting the delta_v calculated from simulation
    result = []
    for i, row in dv_df.iterrows():
        # get master_df row by current cirenid
        cirenid = int(row["cirenid"])
        master_row = master_df.loc[cirenid].copy()
        print(f" - Calculating injury risks for case {cirenid}...")
        # set delta_v used to the calculated delta_v from simulation
        master_row["total_delta_v"] = row["2D_delta_v_av"]
        # run model
        risks = model.calculate_all_risks(master_row)

        result.append({
            'cirenid': cirenid,
            'category': master_row['scenario'],
            'age_yr': master_row['age_yr'],
            'gender': master_row['sex'],
            'height': master_row['height'],
            'weight': master_row['weight'],
            'bmi': master_row['bmi'],
            'iss': master_row['iss'],
            **risks
        })
    
    # save to file
    df = pd.DataFrame(result)
    df.to_csv(output_file)
    print(f"Finished for {len(df)} cases.")


if __name__ == "__main__":
    main(
        "outputs/delta_v_results.csv",
        "outputs/master_cases.xlsx",
        "ciren_database/CISS_injury_models_20210415.xlsx",
        "outputs/sim_injury_risks.csv"
    )

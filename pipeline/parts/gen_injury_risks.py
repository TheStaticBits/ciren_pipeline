import pandas as pd
from pathlib import Path

import ciren.calculate_injury_risks as calc_risk

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
        master_row = master_df[row["cirenid"]]
        print(f" - Calculating for case {row["cirenid"]}...")
        # set delta_v used to the calculated delta_v from simulation
        master_row["total_delta_v"] = row["2D_delta_v_av"]
        # run model
        risks = model.calculate_all_risks(master_row)

        result.append({
            'cirenid': row['cirenid'],
            'category': row['scenario'],
            'age_yr': row['age_yr'],
            'gender': row['sex'],
            'height': row['height'],
            'weight': row['weight'],
            'bmi': row['bmi'],
            'iss': row['iss'],
            **risks
        })
    
    # save to file
    df = pd.DataFrame(result)
    df.to_csv(output_file)
    print(f"Finished for {len(df)} cases.")


if __name__ == "__main__":
    main(
        "pipeline/outputs/delta_v_results.csv",
        "ciren_database/master_cases.xlsx",
        "ciren/CISS_injury_models_20210415.xlsx",
        "pipeline/outputs/sim_injury_risks.csv"
    )
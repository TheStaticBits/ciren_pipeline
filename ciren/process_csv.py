import argparse
import pandas as pd
from pathlib import Path

# folder must contain case CSVs. Usually in Driver-Licensing-Test/output/test-data/test-round-[N]/[test-name]
# optionally, set masses (kg) of AV and challenger
def process_csv(folder: Path, cases: int, verbose: bool, m_av: int=1500, m_ch: int=1500) -> list:
    results = []

    if verbose: print(f"Processing {cases} cases from {folder}.")

    for i in range(cases):
        if verbose: print(f"\nProcessing case {i}...")

        csv_path = folder / f"{i}.csv"
        df = pd.read_csv(csv_path)

        last = df.iloc[-1]   # last row
        timestamp = last["timestamp"]

        # find first row from last that does not have a timestamp of 0
        for i in range(df.size):
            if timestamp != 0: break
            last = df.iloc[-1 - i]
            timestamp = last["timestamp"]
        
        # extract speeds
        v_av = last["AV sp"]
        v_ch = last["challenger sp"]
        
        # conservation of momentum
        v_final = (m_av * v_av + m_ch * v_ch) / (m_av + m_ch)
        delta_v_av = v_final - v_av
        delta_v_ch = v_final - v_ch
        
        results.append({
            "case": i,
            "timestamp": timestamp,
            "AV_sp": v_av,
            "challenger_sp": v_ch,
            "v_final": v_final,
            "delta_v_AV": delta_v_av,
            "delta_v_challenger": delta_v_ch
        })
        
        if verbose:
            print(f"Read: v_av={v_av} | v_ch={v_ch} | timestamp={timestamp}.")
            print(f"Calculated: v_final={v_final} | delta_v_av={delta_v_av} | delta_v_ch={delta_v_ch}")
        
    
    return results


if __name__ == "__main__":
    # Example command: python process_csv.py --cases 1 --input_folder "~/lab/Behavioral-Safety-Assessment/Driver-Licensing-Test/output/Autoware.Universe/test_data/test_round_1/left_turn_straight" 
    parser = argparse.ArgumentParser("Processes crash CSVs and finds change in velocity. Outputs to delta_v_results.csv.")
    parser.add_argument("-i", "--input_folder", help="Folder that contains simulation CSV output files.")
    parser.add_argument("-c", "--cases", help="Number of cases to parse in the input folder.")
    parser.add_argument("-v", "--verbose", help="Sets the program to output statuses as it processses.", action="store_true")
    args = parser.parse_args()

    # process CSV files
    results = process_csv(folder=Path(args.input_folder), cases=int(args.cases), verbose=args.verbose)

    # combine all cases into one dataframe and save to output file
    results_df = pd.DataFrame(results)
    results_df.to_csv("delta_v_results.csv", index=False)
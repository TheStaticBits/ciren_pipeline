import argparse
import pandas as pd
from pathlib import Path

# folder must contain case CSVs. Usually in Driver-Licensing-Test/output/test-data/test-round-[N]/[test-name]
# optionally, set masses (kg) of AV and challenger
# this function returns a list of dictionaries, where each dictionary is a row in an excel or csv file
def process_csv(folder: Path, cirenid: int, cases: int, verbose: bool, m_av: int, m_ch: int) -> list:
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
            "cirenid": cirenid,
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


def main(input: Path, cirenid: int, cases: int, verbose: bool, m_av: int, m_ch: int):
    # process CSV files
    results = process_csv(input, cirenid, cases, verbose, m_av, m_ch)

    # combine all cases into one dataframe and save to output file
    results_df = pd.DataFrame(results)
    results_df.to_csv("delta_v_results.csv", index=False)


if __name__ == "__main__":
    # Example command: python process_csv.py --cases 1 --input "~/lab/Behavioral-Safety-Assessment/Driver-Licensing-Test/output/Autoware.Universe/test_data/test_round_1/left_turn_straight" 
    parser = argparse.ArgumentParser("Processes crash CSVs and finds change in velocity. Outputs to delta_v_results.csv.")
    parser.add_argument("-i", "--input", type=Path, help="Folder that contains simulation CSV output files.")
    parser.add_argument("-id", "--cirenid", type=Path, default=-1, help="Folder that contains simulation CSV output files.")
    parser.add_argument("-c", "--cases", type=int, default=1, help="Number of cases to parse in the input folder.")
    parser.add_argument("-mav", "--m-av", type=int, help="Mass of AV.")
    parser.add_argument("-mch", "--m-ch", type=int, help="Mass of challenger.")
    parser.add_argument("-v", "--verbose", help="Sets the program to output statuses as it processses.", action="store_true")
    args = parser.parse_args()

    main(args.input, args.cirenid, args.cases, args.verbose, args.m_av, args.m_ch)
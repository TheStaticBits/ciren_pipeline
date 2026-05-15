# LLM configuration, usage
# + filtering (exclude cases with not exactly 2 vehicles)

import flatten_exports_to_master as flatten
from pathlib import Path
import os

# Finds each CrashExport-[id]-[date].xlsx file and tests if it has the appropriate number of vehicles.
# returns the ciren_ids that have 2 vehicles.
def filter_num_vehicles(folder: Path, ciren_ids: list[int]) -> list[int]:
    final_ciren_ids: list[int] = []

    print("Filtering cases without 2 vehicles...")
    
    # iterate though the ciren_ids and check if the VEHICLES value is 2.
    # if not, delete the case file.
    for id in ciren_ids:
        file = list(folder.glob(f"CrashExport-{id}-*.xlsx"))[0]
        crash_sheet = flatten._read_sheet(file, "CRASH")
        num_vehicles = flatten._pick(crash_sheet, "VEHICLES", default=2)
        
        if num_vehicles == 2:
            final_ciren_ids.append(id)
        else:
            os.remove(file) # deletes case file

    print(f"Filtered {len(ciren_ids) - len(final_ciren_ids)} cases that do not deal with exactly 2 vehicles!")

    
def main(ciren_ids: list[int]):
    pass
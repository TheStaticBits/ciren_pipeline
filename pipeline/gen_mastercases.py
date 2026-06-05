# ---- Generate mastercases.xlsx from CIREN data chosen ----
# 1. Take in a list of all new cases to generate a MasterCases file of
# 2. Run scrape.py to scrape new cases -- outputs Crash Files to CrashExports folder
# 3. Run scrape_summaries.py to scrape summary of cases. Potentially add PDFs of the cases here for the LLM?
# 4. Tweak LLM categorization into the 14 cases -- make sure to filter out all bad cases. Then output to ciren_crash_summaries_categorized.xlsx
# 5. Run flatten_exports_to_master.py, outputting the data to the master_cases.xlsx file.

from pathlib import Path

import ciren_database.scrape as scrape
import ciren_database.scrape_summary as scrape_summary
import ciren_database.categorize as categorize
import ciren_database.flatten_exports_to_master as flatten

def gen_master_cases(abs_path: Path, case_nums: list[int]):
    # 1. Run scrape.py
    print("1. Scraping crashes...")
    scrape.main(abs_path / Path("ciren_database/CrashExports"), case_nums)
    print("1. Scraping crashes complete!")

    # Filter out cases that do not involve 2 vehicles.
    case_nums = categorize.filter_num_vehicles(Path(abs_path / Path("ciren_database/CrashExports")), case_nums)

    # 2. Run scrape_summaries.py on the rest of the cases
    print("2\n\n. Scraping crash summaries...")
    case_nums = scrape_summary.main(Path("ciren_database/CrashExports"), Path("ciren_database/ciren_crash_summaries.xlsx"), case_nums)
    print("2. Scraping crash summaries complete!")

    # 3. Use LLM API to categorize into one of the 14 available, filtering out bad cases
    # TODO
    print("\n\n3. Categorizing crashes...")
    categorize.main(case_nums, Path("ciren_database/ciren_crash_summaries.xlsx"), Path("ciren_database/ciren_crash_summaries_categorized.xlsx"))
    print("3. Categorizing crashes complete!")

    # 4. Run flatten_exports_to_master.py, excluding cases that were not categorized in step 3
    print("\n\n4. Flattening crash data into master file...")
    flatten.main(Path("ciren_database/CrashExports"), Path("ciren_database/master_cases.xlsx"), Path("ciren_database/ciren_crash_summaries_categorized.xlsx"), 0, None, 25)
    print("4. Finished flattening crash data!")


if __name__ == "__main__":
    with open("input_cases.txt", "r") as file:
        ciren_ids = [int(id) for id in file.read().split(" ")]
        gen_master_cases(Path(__file__).parent, ciren_ids)
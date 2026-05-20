# This file runs gen_injuryanalysis and gen_mastercases in the pipeline folder,
# bridging all of the steps from processing cases to injury analysis.

# STEPS:

# ---- Generate MasterCases from CIREN data chosen ----
# 1. Take in a list of all new cases to generate a MasterCases file of
# 2. Run scrape.py to scrape new cases -- outputs Crash Files to CrashExports folder
# 3. Run scrape_summaries.py to scrape summary of cases. Potentially add PDFs of the cases here for the LLM?
# 4. Tweak LLM categorization into the 14 cases -- make sure to filter out all bad cases. Then output to ciren_crash_summaries_categorized.xlsx
# 5. Run flatten_exports_to_master.py, outputting the data to the master_cases.xlsx file.

# ---- After master cases has been generated ----
# 1. read and extract data from MasterCases file
# 2. Take categorization and take input speeds, change the max speed to match (in m/s) the EDR data from the MasterCases file using edit_speed.py
# 3. Edit output/Autoware.Universe/case JSON files as necessary, particularly relative_sp or sp, with some random variation.
# 4. Run all cases (as many as there are in the case JSON file for a particular case)
# 5. Determine what cases have resulted in a collision using the results.csv file in outputs/test_data
# 6. Run collision cases through ciren/process_csv.py to calculate the delta-v of a collision
# 7. Run new delta-v data through injury calculator file in ciren/calculate_injury_risks.py
# 8. Run statistical analysis on the difference in injury risks from a human driver compared to an automatic vehicle.

import pipeline.gen_mastercases
import pipeline.gen_injuryanalysis

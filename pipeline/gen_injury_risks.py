# ---- After master cases has been generated ----
# 1. read and extract data from MasterCases file
# 2. Take categorization and take input speeds, change the max speed to match (in m/s) the EDR data from the MasterCases file using edit_speed.py
# 3. Edit output/Autoware.Universe/case JSON files as necessary, particularly relative_sp or sp, with some random variation.
# 4. Run all cases (as many as there are in the case JSON file for a particular case)
# 5. Determine what cases have resulted in a collision using the results.csv file in outputs/test_data
# 6. Run collision cases through ciren/process_csv.py to calculate the delta-v of a collision
# 7. Run new delta-v data through injury calculator file in ciren/calculate_injury_risks.py
# 8. Run statistical analysis on the difference in injury risks from a human driver compared to an automatic vehicle.

import asyncio
import pipeline.parts.gen_case_parameters as gen_case_parameters
import pipeline.parts.run_cases as run_cases

# runs gen_case_parameters and then run_cases.py
async def gen_injury_risks():
    gen_case_parameters.main()
    await run_cases.main()

if __name__ == "__main__":
    asyncio.run(gen_injury_risks())
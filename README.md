# CIREN Pipeline

### Pipeline Stages

1. Download CIREN case export excel files (`outputs/CrashExports/CrashExport-*.xlsx`)
2. Filter out cases that do not involve specifically 2 vehicles
3. Scrape crash summaries for the remaining cases
4. Categorize cases into predefined scenarios using Gemini, and filter out any that do not match the strict 11 cases that can be simulated
5. Build a master case table (one row per case) of all of the data we have gathered so far
6. Computer JSON case parameters based on the master case table
7. Set max speed, parameters in DLT and simulate each scenario
8. Calculate 2-dimensional delta-V for each simulated case
9. Calculate 2-dimensional delta-V for each real case using the scraped crash summaries

<br />

*Notes:*
- Steps 1-5 should be completed in the `ciren_database` folder (web scraping and organizing data into a master Excel sheet `master_cases.xlsx`).
- Steps 6–8 should be completed in the `pipeline` folder (simulating scenario).
- Step 9 is completed in the `ciren` folder (calculating real case delta-V from crash summaries).

## Quick Start

- In `pipeline/parts/run_cases.py`, change the `DLT_PATH` variable to point to the path of the Driver Licensing Test folder in the Behavioral Safety Assessment respository on your computer.
    - Also change `DLT_PATH` in `pipeline/parts/edit_speed.py` if you plan on running edit_speed manually (otherwise this is not necessary).
- If you would like to run the categorization step with your Gemini Pro (bewared, you may be temporarily restricted from using Gemini for a while if you run too many cases through it), in `ciren_database/categorize.py`, change `USE_CHROME_PROFILE` to `True`, and set `CHROME_PROFILE` and `CHROME_BINARY`. You may want to make a copy of your Chrome profile folder elsewhere on your device and set `CHROME_PROFILE` to point to that copy instead of directly to the profile, if you run into issues running categorize.py with these parameters set.
- Edit `input_cases.txt` to include the case IDs of the cases you want to simulate, separated by one space each.
- Then run the following commands in the root directory to run the whole pipeline:
```bash
conda activate terasim-cosim
pip install -r requirements.txt

python -m pipeline.gen_mastercases
python -m pipeline.gen_injury_risks
```
- If the Gemini categorization step pauses without sending another question after the AI has responded, press enter and let it continue. 
- The output of the injury risks of the simulated cases can be found in `outputs/sim_injury_risks.csv`.
- To calculate injury risks on the scraped cases with real data, run the following command:
```bash
python -m ciren.calculate_injury_risks
```
- This will output to `outputs/injury_risk_calculations.csv`.

## In-depth Overview of each File
- in progress

## Updates:
- To compile SRV files necessary for Autoware ROS integration used in `pipeline/parts/autoware_ros_client.py`, run the following commands from the root directory:
```bash
cd tier4_system_msgs
colcon build
```

- Edit these Autoware config files to make the simulation more accurate:
`autoware/src/universe/autoware.universe/planning/motion_velocity_smoother/config/default_motion_velocity_smoother.param.yaml`
`autoware/src/launcher/autoware_launch/autoware_launch/config/planning/scenario_planning/common/common.param.yaml`
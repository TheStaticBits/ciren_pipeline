## Running UMTRI notes

### run Carla with everything:
```bash
# Terminal 1
cd ~/lab/carla/CARLA_0.9.15
./CarlaUE4.sh
```

```bash
# Terminal 2
conda activate terasim-cosim
cd ~/lab/mcity_digital_twin/CARLA/scripts
python load_mcity_digital_twin.py
```


### Terminal 1, run autoware.
- ros2 launch autoware_launch should be run in `(base)` venv which is on by default, using:
```bash
# adjusted map
ros2 launch autoware_launch planning_simulator.launch.xml map_path:=$HOME/lab/ciren_pipeline/map vehicle_model:=sample_vehicle sensor_model:=sample_sensor_kit lanelet2_map_file:=lanelet2_mcity_stable.osm

# their map
ros2 launch autoware_launch planning_simulator.launch.xml map_path:=$HOME/lab/autoware/map vehicle_model:=sample_vehicle sensor_model:=sample_sensor_kit lanelet2_map_file:=lanelet2_mcity.osm
```

### Terminal 2, run terasim_cosim
- To run autoware_cosim with terasim_cosim, `conda deactivate` and then run the command that you have either from [here](https://github.com/michigan-traffic-lab/Behavioral-Safety-Assessment/tree/main) or [here](https://github.com/michigan-traffic-lab/TeraSim-Mcity-2.0/blob/main/autoware.md).
  - Notes: Used python3 root and installed TeraSim & TeraSim CoSim using `--user` and `-e` to symlink to TeraSim source installation in `"~/lab/TeraSim/Source Code"`. Used `chmod` to fix file permissions to do so. 
```bash
conda deactivate

ros2 launch mcity_abc mcity_abc.launch.py scenario:="car_following"
```

- if it throws a module not found error, run these:
```bash
/usr/bin/python3 -m pip install --user -e "/home/mzjia/lab/Behavioral-Safety-Assessment/Source Code/TeraSim"
/usr/bin/python3 -m pip install --user -e "/home/mzjia/lab/Behavioral-Safety-Assessment/Source Code/Terasim-Cosim"
```

- If running a TeraSim/example example, use:
```bash
conda activate terasim-cosim
python3 default_sumo_example.py
```

### Terminal 3, run a test
- Set conda to terasim-cosim. 
- Run a particular test, from the Driver Licensing Test. Add --gui for gui. If using autoware, background vehicles should appear in rviz. Then, click auto to run and start driving the vehicle. 
```bash
conda activate terasim-cosim

cd Driver-Licensing-Test

python3 DLT.py --gui --scenario "car_following" --case-num 0 --round-num 1
```
- If there is a module not found error, reinstall the conda environment using:
```bash
cd ~/lab/Behavioral-Safety-Assessment

conda deactivate
conda env create -f terasim-cosim.yaml
conda activate terasim-cosim
```
- If that does not work, wipe and reinstall the conda environment using:
```bash
cd ~/lab/Behavioral-Safety-Assessment

conda deactivate
conda env remove -n terasim-cosim
conda env create -f terasim-cosim.yaml
conda activate terasim-cosim
```

<br />

## Notes from Tuesday, May 12th
- Google Drive folder has been shared, containing CIREN Master Data.
- Analyze 10 successfully by Thursday from the bottom up.
- Also analyze the meaning of the different parameters for each of the 12 test cases -- put information about them into a Google Doc in the same shared folder.
- Begin work on the Python automated pipeline for running the simulation on each successful CIREN case, running the delta-v calculations, and the injury calculations.

<br />

## Notes from Tuesday, May 19th
 - Fix delta-v lat/lon scraping bug from the excel files outputting to master-cases
 - Focus on the processing and automated pipeline
 - Make a JSON output file that stores the case ID, the case type, and the case parameters for each case
 - Automate processing that JSON file and simulating each case in that JSON file, and then outputting the delta-v and injury calculations for each case in an excel file.

<br />

## Notes from Tuesday, May 26th
- ✓ Look through config.yaml files and try to understand what does what
- ✓ Find one demo case for each of the test cases for the MCity meeting
- ✓ Change delta-v calculations to be in both x and y directions
- ✓ Write injury-risk calculation code to iterate through outputs/case_parameters.json
- ✓ LLM for categorization
    - check LLM categorization

clarification questions prior to May 26th meeting:
- should I use webscraper in order to plug into an LLM to categorize the cases? Or should I just do it manually?
- how do we ensure better accuracy with the case parameters etc. etc.
- for injury calculations, are we using the same injury risk information (bmi, etc.) as the case data along with the delta-v of the collisions in order to calculate the injury risk?
- are we plugging in our own heading angle into the injury risk calculation?
- are we doing pedestrian vehicle simulations as well? or just vehicle-vehicle simulations?

<br />

## Notes from Tuesday, June 2nd
- Try to connect CARLA, Autoware, TeraSim together
- Fix bug with case parameters.json duplicating cases
- Write up and document each of the files in the codebase and how to run them, etc.
- ✓ Look through the config.yaml files and try to understand what does what
- ✓ Find one demo case for each of the test cases for the MCity meeting
- ✓ Write up each parameter in config.yaml file in a Google Doc to see what it does and how it affects the simulation

<br />

## Notes from Tuesday, June 9nd
- Try to connect CARLA, Autoware, TeraSim all together
- Try to adjust Autoware position to match SUMO, or vice versa
- Try to figure out how to adjust Autoware AV speed or positions
- Try to automate running Autoware.
- Fix bug with case parameters.json duplicating cases


## for June 16th
- autoware acceleration to max velocity (vehicle_cmd_gate/config/vehicle_cmd_gate_param.yaml)
- adjust BV parameter generation more
- left_turn_turn has max speed of 10, see if possible to make it quicker than 10.
- bug fixing
- hooking into CARLA for triple-cosim visualization
- injury risk comparison graphical representation?

## Notes from Tuesday, June 16th
- Get CARLA working
- Generate graph of "max_speed" versus actual AV speed 5 seconds before collision (in DLT output) for each of the three cases, to see if there's a cap, and see if we can adjust that max speed to match the case's known speed. 
- If that does not work and we can't adjust that manually, see if there is a way to set the AV at a location 5 seconds before the crash directly, with a set speed already. Then, see if we can change how the BV behaves to fast-forward it to 5 seconds before the crash. This would allow us to skip to the moment before the crash and see how the AV handles it.

### [JOSM](https://chatgpt.com/c/6a395a33-37fc-83ea-8a2c-eff74d755476)
- Run with `josm` in terminal.
- Open filter by `Alt + Shift + F`, type `type:node` and hit `select`
- Toggle between freehand and square select by pressing `S`
- Select roads and press `Ctrl + F` and type `type:relation type=lanelet parent selected` to get the lanelet options
- Then change speed_limit in the sidebar.

### stop_at_goal
```bash
ros2 param get /planning/scenario_planning/motion_velocity_smoother stop_at_goal
```

### Things done:
- Changed min/max acc/jerk
- Added stop_at_goal ros2 flag to allow faster speeds through the whole course of motion
- Added ros2 subscription to set the vehicle speed without impacting its position or rotation
- Changed JOSM map speed limits (and position?)

## Notes from Tuesday, June 23rd
- Update gen_case_parameters.py to more accurately fit the cases
- Adjust time that the speed is set so that it is approximately the correct speed 5 seconds before collision
- Change road speed limits to not impact vehicle speed
- Run 50-100 cases


## Notes from Tuesday, June 23rd
- Create slide based on how the pipeline works, how the gen_case_parameters works, etc.
- Adjust and fix the remaining issues with the pipeline (simulation breaking etc.)
  - Find issue with autoware that slows it down to around 42 kph on the long road
  - Fix turns (too high speed, speed set too late)
  - Fix vehicle encroachment for not resulting in collisions (delay longer)
  - Fix lane departure opposite BV not moving sometimes
- Send resulting 50 cases of data injury risks to Anne
## Running UMTRI notes

### Terminal 1, run autoware.
- ros2 launch autoware_launch should be run in `(base)` venv which is on by default, using:
```bash
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
- Look through config.yaml files and try to understand what does what
- Find one demo case for each of the test cases for the MCity meeting
- ✓ Change delta-v calculations to be in both x and y directions
- ✓ Write injury-risk calculation code to iterate through pipeline/outputs/case_parameters.json
- LLM for categorization

clarification questions prior to May 26th meeting:
- should I use webscraper in order to plug into an LLM to categorize the cases? Or should I just do it manually?
- how do we ensure better accuracy with the case parameters etc. etc.
- for injury calculations, are we using the same injury risk information (bmi, etc.) as the case data along with the delta-v of the collisions in order to calculate the injury risk?
- are we plugging in our own heading angle into the injury risk calculation?
- are we doing pedestrian vehicle simulations as well? or just vehicle-vehicle simulations?
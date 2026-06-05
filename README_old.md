# 🚗 CIREN Pipeline

## 📌 Overview

This project implements a 6-stage pipeline to process CIREN crash data, classify scenarios, and compute injury risks.

### Pipeline Stages

1. Download CIREN case exports (`CrashExport-*.xlsx`)
2. Scrape crash summaries
3. Categorize cases into predefined scenarios
4. Build a master case table (one row per case)
5. Compute simulation delta-V
6. Compute injury risk outputs

* Steps 1-4 should be completed in the `ciren_database` folder (web scraping and organizing data into a master Excel sheet `master_cases.xlsx`).
* Steps 5–6 should be completed in the `ciren` folder (calculating `delta_v` and generating injury predictions).
---

## 1️⃣ Download CIREN Case Exports

### ▶️ Run

```bash
# navigate to ciren_database directory
cd ciren_database
# run python script
python scrape.py
```

### ⚙️ What it does

* Downloads one `CrashExport-*.xlsx` file per CIREN case ID

### 🔧 Config (`scrape.py`)

* `DOWNLOAD_FOLDER`: folder where downloaded files are saved
* `cirenids`: the ciren case ids you would like to scrape

### 📤 Output

* Files like:

```
CrashExport-15-4-9-2026.xlsx
```

---

## 2️⃣ Scrape Crash Summaries

### ▶️ Run

```bash
python scrape_summary.py
```

### ⚙️ What it does

* Opens each CIREN case page
* Extracts the **Crash Summary**
* Writes results to an Excel file

### 📄 Output columns

* `cirenid`
* `crash_summary`

### 🔧 Config (`scrape_summary.py`)

* `OUTPUT_FILE`: output Excel file path
* `DOWNLOAD_FOLDER`: only affects Chrome download preferences (can be any existing folder)
* `cirenids`: the ciren case ids you would like to scrape

### 📤 Output

```
ciren_crash_summaries.xlsx
```

---

## 3️⃣ Categorize Scenarios

Ask your favorite LLM to classify each case into one of the following:

```python
SCENARIOS = [
    "car_following",
    "cut_in",
    "lane_departure_opposite",
    "lane_departure_same",
    "left_turn_straight",
    "left_turn_turn",
    "right_turn_straight",
    "right_turn_turn",
    "roundabout_av_inside",
    "roundabout_av_outside",
    "traffic_signal",
    "vehicle_encroachment",
    "vru_at_crosswalk",
    "vru_without_crosswalk",
]
```

### 📌 Rules

* Keep only rows matching one of the scenarios
* Drop rows with missing or empty `crash_summary`
* Do not create new categories

### 📄 Required output columns

* `cirenid`
* `crash_summary`
* `scenario`

### 📤 Output

```
ciren_crash_summaries_categorized.xlsx
```
* Depending on how you go about this, you may need to create your own xlsx file and copy/paste the LLM output
* Add this xlsx file to the `ciren_database` folder.

---

## 4️⃣ Build Master Case Spreadsheet

### ▶️ Run

```bash
python flatten_exports_to_master.py
```

### ⚙️ What it does

* Reads downloaded `CrashExport-*.xlsx` files
* Merges with categorized summaries
* Filters to categorized cases only
* Produces one row per case

### 🔧 Config (`flatten_exports_to_master.py`)

* `DEFAULT_INPUT`: folder with `CrashExport-*.xlsx` (DOWNLOAD_FOLDER from Step 1)
* `DEFAULT_CATEGORIZED`: categorized file from Step 3
* `DEFAULT_OUTPUT`: output file path

### 📤 Output

Master Excel file containing:

* Case info
* Vehicle data
* EDR data
* CDC
* `crash_summary`
* `scenario`

---

## 5️⃣ Compute Delta-V from Simulation CSVs

### ▶️ Run

```bash
cd ciren
python process_csv.py --cases 1 --input_folder "~/lab/Behavioral-Safety-Assessment/Driver-Licensing-Test/output/Autoware.Universe/test_data/test_round_1/lane_departure_opposite" --verbose
```

### ⚙️ What it does

* Processes simulation CSV files named `0.csv`, `1.csv`, and so on inside the input folder
* Computes collision delta-V assuming **perfectly inelastic collision**

### 🔧 CLI (`process_csv.py`)

Required arguments:

* `-i` / `--input_folder`: folder containing the simulation CSV files
* `-c` / `--cases`: number of CSV files to process
* `-v` / `--verbose`: optional flag that prints progress while processing

Example:

```python
python process_csv.py --cases 1 --input_folder "~/lab/Behavioral-Safety-Assessment/Driver-Licensing-Test/output/Autoware.Universe/test_data/test_round_1/lane_departure_opposite"
```

Default vehicle masses are set in `process_csv.py` at `m_av=1500` and `m_ch=1500`. If you need different masses, update the function defaults in the script.

### 📤 Output

`delta_v_results.csv` file with columns:

```
case, timestamp, AV_sp, challenger_sp, v_final, delta_v_AV, delta_v_challenger
```

---

## 6️⃣ Compute Injury Risks

### ▶️ Run

```bash
python calculate_injury_risks.py
```
### ⚙️ What it does

* Calculates injury risks using the CISS injury model for each case in `cases_file`.

### 📌 Requirements

* `CISS_injury_models_20210415.xlsx` must be in the same directory
* Input dataset must match expected schema (if you are using `master_cases.xlsx` you do not need to change anything)

### 🔧 Config

* Set `cases_file` to the location of your `master_cases.xlsx` file (the file generated from Step 4)
* Note: The current implementation uses `edr_total_delta_v_kmph` from the scraped dataset as `delta_v`. To use a different source (e.g., the calculated `delta_v`s from Step 5), update the line:
`'delta_v': row['edr_total_delta_v_kmph']` to read from the file or field containing your desired delta_v values.

### 📤 Output

`injury_risk_calculations.csv` inside the `injury_risk_outputs` folder with fields such as:

```
cirenid, category, age_yr, gender, height, weight, bmi, delta_v,
iss, direction, ..., Head_Risk, Chest_Risk, LowerExtremity_Risk
```

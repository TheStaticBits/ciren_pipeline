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
# navigate to ciren directory
cd ..
cd ciren
# run python script
python process_csv.py
```

### ⚙️ What it does

* Processes simulation CSVs
* Computes collision delta-V assuming **perfectly inelastic collision**

### 🔧 Config (`process_csv.py`)

Update before running:

* Input folder path `folder` containing your simulation csv files (0.csv, 1.csv, etc.)
* Vehicle masses:
  * `m_av`
  * `m_ch`
* File loop range:

```python
for i in range(...)
```
where range is the number of simulation csv files you have in `folder`.

### 📤 Output

CSV with columns:

```
case, timestamp, AV_sp, challenger_sp, v_final, delta_v_AV, delta_v_challenger
```

---

## 6️⃣ Compute Injury Risks

### ▶️ Run

```bash
python calculate_injury_risks.py
```

### 📌 Requirements

* `CISS_injury_models_20210415.xlsx` must be in the same directory
* Input dataset must match expected schema

### 🔧 Config

* Set output filename/path inside the script (e.g., `output_csv`)
* Note: The current implementation uses `edr_total_delta_v_kmph` from the scraped dataset as `delta_v`. To use a different source (e.g., the calculated `delta_v` from Step 4 simulation output), update the line:
`'delta_v': row['edr_total_delta_v_kmph']` to read from the file or field containing your desired delta_v values.

### 📤 Output

CSV with fields such as:

```
cirenid, category, age_yr, gender, height, weight, bmi, delta_v,
iss, direction, ..., Head_Risk, Chest_Risk, LowerExtremity_Risk
```

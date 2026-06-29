# LLM configuration, usage
# + filtering (exclude cases with not exactly 2 vehicles)

from __future__ import annotations

import os, time, pandas as pd
from pathlib import Path
import ciren_database.flatten_exports_to_master as flatten

VALID = ["None", "cut_in", "car_following", "lane_departure_same", "lane_departure_opposite", 
         "left_turn_straight", "left_turn_turn", "right_turn_straight", "right_turn_turn",
         "roundabout_av_outside", "roundabout_av_inside", "vehicle_encroachment"]

TRIES = 3

USE_CHROME_PROFILE = False
CHROME_PROFILE = "/home/mzjia/chrome-profile/google-chrome"
CHROME_BINARY = "/usr/bin/google-chrome"


def load_existing_categorizations(output_file: Path) -> tuple[pd.DataFrame, set[int]]:
    if not output_file.exists():
        return pd.DataFrame(columns=["cirenid", "scenario", "crash_summary"]), set()

    existing = pd.read_excel(output_file)
    existing = existing.loc[:, ~existing.columns.astype(str).str.startswith("Unnamed")]
    if "cirenid" not in existing.columns:
        return pd.DataFrame(columns=["cirenid", "scenario", "crash_summary"]), set()

    ids = {
        int(cirenid)
        for cirenid in existing["cirenid"].dropna()
    }
    return existing, ids


def save_categorizations(output_file: Path, rows: list[dict]) -> None:
    output = pd.DataFrame(rows)
    output.to_excel(output_file, index=False)

def get_prompt(cirenid: int, summary: str) -> str:
    return f"""Categorize the following car crash, found at: https://crashviewer.nhtsa.dot.gov/ciren/details/{cirenid}/ciren-summary-document. The summary of this case is pasted here from the link above:
        {summary}

        ---------

        ONLY RESPOND with one of the following 12 case categorizations, and nothing more nothing less, according to the crash diagram at the link and/or the summary pasted above. Respond with only "None" if it does not fit the details of any of the categories exactly, or does not involve exactly 2 vehicles. The distinction between Vehicle 1 and Vehicle 2 is important, and if the scenario is switched, it has to be "None", unless another scenario matches the case exactly.

        cut_in: Both vehicles involved are traveling in lanes one next to each other, and Vehicle 2 is in front of Vehicle 1. Vehicle 2 merges into Vehicle 1's lane in front of Vehicle 1, resulting in a crash.
        car_following: Both vehicles are traveling in a single lane, where Vehicle 2 is traveling in front of Vehicle 1. A rearend occurs, for whatever reason.
        lane_departure_same: Same scenario as "cut_in", however, Vehicle 2 does not intend to switch lanes and drifts into Vehicle 1's lane by accident.
        lane_departure_opposite: Vehicle 1 is traveling in one direction, and Vehicle 2 is traveling in the exact opposite parallel direction in the lane next to Vehicle 1. Vehicle 2 drifts out of its lane and into Vehicle 1's lane, resulting in a crash.
        left_turn_straight: Vehicle 1 is traveling straight through an intersection, and Vehicle 2 starts traveling in the exact opposite parallel  direction from Vehicle 1. Vehicle 2 intends to turn left at this intersection, and turns left in front or into Vehicle 1. The two vehicles cannot be entering the intersection traveling perpendicularly to one another.
        left_turn_turn: Same scenario as "left_turn_straight", however, Vehicle 1 is the one that is turning instead of Vehicle 2, which is intending to travel straight through this intersection. They are still starting going in exact opposite directions.
        right_turn_turn: Vehicle 1 is turning right at an intersection, and Vehicle 2 is traveling straight through the same intersection. Vehicle 1 is intending to turn right and start heading down the same direction as Vehicle 2, to turn into the same lane that Vehicle 2 is traveling in. The vehicles have to start the scenario perpendicularly to one another.
        right_turn_straight: Opposite scenario to "right_turn_turn" -- Vehicle 2 is turning right, and Vehicle 1 is traveling straight through the intersection. They are still at a 90 degree angle to each other to start with.
        roundabout_av_outside: Vehicle 2 is turning around inside of a roundabout. Vehicle 1 is entering the roundabout, and the two collide.
        roundabout_av_inside: Vehicle 1 is turning around inside of a roundabout. Vehicle 2 is entering the roundabout, and the two collide.
        vehicle_encroachment: Vehicle 1 is traveling straight, and Vehicle 2 is stopped on the road or traveling perpendicularly to Vehicle 1. Vehicle 1 hits Vehicle 2.
        
    """


# Finds each CrashExport-[id]-[date].xlsx file and tests if it has the appropriate number of vehicles.
# returns the ciren_ids that have 2 vehicles.
def filter_num_vehicles(folder: Path, ciren_ids: set[int]) -> set[int]:
    final_ciren_ids: set[int] = set()

    print("Filtering cases without 2 vehicles...")
    
    # iterate though the ciren_ids and check if the VEHICLES value is 2.
    # only add it to final_ciren_ids if it has 2
    for id in ciren_ids:
        file = list(folder.glob(f"CrashExport-{id}-*.xlsx"))[0]
        crash_sheet = flatten._read_sheet(file, "CRASH")
        num_vehicles = flatten._pick(crash_sheet, "VEHICLES", default=2)
        
        if num_vehicles == 2:
            final_ciren_ids.add(id)

    print(f"Filtered {len(ciren_ids) - len(final_ciren_ids)} cases that do not deal with exactly 2 vehicles!")
    return final_ciren_ids


def wait_for_editable_element(driver, timeout: int = 30):
    from selenium.webdriver.support.ui import WebDriverWait

    def find_editable_element(driver):
        return driver.execute_script(
            """
            const selectors = ['textarea', 'input', '[contenteditable="true"]'];

            function isVisible(element) {
                const style = window.getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
            }

            function search(root) {
                for (const selector of selectors) {
                    const matches = root.querySelectorAll(selector);
                    for (const element of matches) {
                        if (isVisible(element) && !element.disabled && !element.readOnly) {
                            return element;
                        }
                    }
                }

                for (const host of root.querySelectorAll('*')) {
                    if (host.shadowRoot) {
                        const found = search(host.shadowRoot);
                        if (found) {
                            return found;
                        }
                    }
                }

                return null;
            }

            return search(document);
            """
        )

    return WebDriverWait(driver, timeout).until(find_editable_element)

def wait_for_response(num: int, driver, timeout: int = 180):
    from selenium.webdriver.support.ui import WebDriverWait

    def find_response(driver):
        result = driver.execute_script(
            """
            const results = [];

            function collectResponses(root) {
                for (const match of root.querySelectorAll("model-response")) {
                    const paragraph = match.querySelector("p");
                    if (paragraph && paragraph.textContent) {
                        results.push(paragraph.textContent.trim());
                    }
                }

                for (const host of root.querySelectorAll("*")) {
                    if (host.shadowRoot) {
                        collectResponses(host.shadowRoot);
                    }
                }
            }

            collectResponses(document);
            return results;
            """
        )

        return result[-1] if len(result) >= num else False

    return WebDriverWait(driver, timeout).until(find_response)

def wait_for_finish_to_send(driver):
    from selenium.webdriver.support.ui import WebDriverWait

    def test_mic(driver):
        return driver.execute_script(
            """
            const button = document.querySelector('[aria-label="Send message"]');
            return button !== null
            """
        )
    return WebDriverWait(driver, 30).until(test_mic)

# Assumes you have Gemini Pro, hooking into your browser,
# typing prompts and receiving categorizations 10 at a time.    
def main(ciren_ids: list[int] | set[int] | None, input_summaries_file: Path, output_file: Path):
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    existing_df, existing_ids = load_existing_categorizations(output_file)

    # load input summaries
    df = pd.read_excel(input_summaries_file)
    cases_to_categorize = set()
    for case in df.itertuples():
        case_id = int(case.cirenid)
        if case_id not in ciren_ids:
            continue
        if case_id in existing_ids:
            print(f"Skipping case {case_id}: already categorized in {output_file}")
            continue
        cases_to_categorize.add(case)

    if not cases_to_categorize:
        print(f"Categorization complete. All requested cases are already categorized in {output_file}.")
        return ciren_ids

    import pyperclip
    from selenium import webdriver
    from selenium.webdriver.common.keys import Keys

    options = webdriver.ChromeOptions()
    if USE_CHROME_PROFILE:
        options.add_argument(f"--user-data-dir={CHROME_PROFILE}")
        options.add_argument("--profile-directory=Default")
        options.add_argument("--remote-debugging-port=9222")
        options.binary_location = CHROME_BINARY
    driver = webdriver.Chrome(options=options)
    driver.get("https://gemini.google.com/app")
    time.sleep(1.0)

    # find the actual editable element inside Gemini's custom input component
    text_box = wait_for_editable_element(driver)
    text_box.click()

    result = existing_df.to_dict("records")
    curr_response = 1

    # iterate through all cases
    for i, case in enumerate(sorted(cases_to_categorize), 1):
        case_id = int(case.cirenid)
        print(f"[{i}/{len(cases_to_categorize)}] Categorizing {case_id}...")

        for _ in range(TRIES):
            # send prompt
            p = get_prompt(case_id, case.crash_summary)
            pyperclip.copy(p) # copy prompt into clipboard
            text_box.click()
            text_box.send_keys(Keys.CONTROL, "v") # paste
            wait_for_finish_to_send(driver) # wait for the send button to load
            text_box.send_keys(Keys.RETURN) # send

            # wait for valid response, then append and break
            response = wait_for_response(curr_response, driver)
            curr_response += 1

            # validate response
            if not response or response not in VALID: continue
            print(f"       Result: {response}")
            result.append({
                "cirenid": case_id,
                "scenario": str(response),
                "crash_summary": case.crash_summary,
            })

            # output result to file
            save_categorizations(output_file, result)
            break

        else:
            print(f"[WARNING] Skipping case {case_id}. Response: {response}")


if __name__ == "__main__":
    main(None, "outputs/ciren_crash_summaries.xlsx", "outputs/ciren_crash_summaries_categorized.xlsx")

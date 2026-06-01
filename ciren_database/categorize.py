# LLM configuration, usage
# + filtering (exclude cases with not exactly 2 vehicles)

import os, time, pyperclip, pandas as pd
from pathlib import Path
import flatten_exports_to_master as flatten

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys

VALID = ["None", "cut_in", "car_following", "lane_departure_same", "lane_departure_opposite", 
         "left_turn_straight", "left_turn_turn", "right_turn_straight", "right_turn_turn",
         "roundabout_av_outside", "roundabout_av_inside", "vehicle_encroachment"]

TRIES = 3


def get_prompt(cirenid: int, summary: str) -> str:
    return f"""
        Categorize the following car crash, found at: https://crashviewer.nhtsa.dot.gov/ciren/details/{cirenid}/ciren-summary-document. The summary of this case is pasted here from the link above:
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


def wait_for_editable_element(driver: webdriver.Chrome, timeout: int = 30):
    def find_editable_element(driver: webdriver.Chrome):
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

def wait_for_response(num: int, driver: webdriver.Chrome, timeout: int = 180):
    def find_response(driver: webdriver.Chrome):
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

def wait_for_finish_to_send(driver: webdriver.Chrome):
    def test_mic(driver: webdriver.Chrome):
        return driver.execute_script(
            """
            const button = document.querySelector('[aria-label="Send message"]');
            return button !== null
            """
        )
    return WebDriverWait(driver, 30).until(test_mic)

# Assumes you have Gemini Pro, hooking into your browser,
# typing prompts and receiving categorizations 10 at a time.    
def main(ciren_ids: list[int], input_summaries_file: Path, output_file: Path):

    options = webdriver.ChromeOptions()
    # options.add_argument("--user-data-dir=/home/mzjia/chrome-profile/google-chrome")
    # options.add_argument("--profile-directory=Default")
    # options.add_argument("--remote-debugging-port=9222")
    options.binary_location = "/usr/bin/google-chrome"
    driver = webdriver.Chrome(options=options)
    driver.get("https://gemini.google.com/app")
    time.sleep(1.0)

    # load input summaries
    df = pd.read_excel(input_summaries_file)

    # find the actual editable element inside Gemini's custom input component
    text_box = wait_for_editable_element(driver)
    text_box.click()

    result = []
    curr_response = 1

    # # iterate through all cases
    for case in df.itertuples():
        if ciren_ids and case.cirenid not in ciren_ids:
            continue

        for _ in range(TRIES):
            # send prompt
            p = get_prompt(case.cirenid, case.crash_summary)
            pyperclip.copy(p)
            text_box.click()
            text_box.send_keys(Keys.CONTROL, "v")
            wait_for_finish_to_send(driver)
            text_box.send_keys(Keys.RETURN)

            # wait for valid response, then append and break
            response = wait_for_response(curr_response, driver)
            curr_response += 1

            # validate response
            if not response or response not in VALID: continue
            if response and response == "None": break

            result.append({
                "cirenid": case.cirenid,
                "scenario": response,
                "crash_summary": case.crash_summary,
            })

            # output result to file
            output = pd.DataFrame(result)
            output.to_excel(output_file)
            break

        else:
            print(f"[WARNING] Skipping case {case.cirenid}. Response: {response}")


if __name__ == "__main__":
    main(None, "ciren_database/ciren_crash_summaries.xlsx", "ciren_database/ciren_crash_summaries_categorized.xlsx")
# LLM configuration, usage
# + filtering (exclude cases with not exactly 2 vehicles)

import os
from pathlib import Path
import flatten_exports_to_master as flatten

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import 

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


# Assumes you have Gemini Pro, hooking into your browser,
# typing prompts and receiving categorizations 10 at a time.    
def main(ciren_ids: list[int], input_summaries_file: Path, output_file: Path):
    options = webdriver.FirefoxOptions()
    driver = webdriver.Firefox(options=options)
    driver.get("https://gemini.google.com/app")

    # find typing box
    text_box = driver.find_element(by=By.TAG_NAME, value="rich-textarea")
    text_box.send_keys("TEST. Send exactly the following text: 'HELLO.'")
    text_box.send_keys(Keys.RETURN)
import os
import glob
import csv
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ─── CONFIG ────────────────────────────────────────────────────────────────────
INPUT_DIR       = "product_url"         # folder containing your .csv files
OUTPUT_DIR      = "scraped_results"     # folder to write one CSV per input
HEADLESS        = False
PAGE_LOAD_PAUSE = 3
POPUP_PAUSE     = 1
DETAILS_PAUSE    = 1

# ─── SETUP FUNCTIONS ────────────────────────────────────────────────────────────
def init_driver(headless=True):
    opts = Options()
    if headless:
        opts.add_argument("--headless")
        opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(10)
    return driver

def close_signup_popup(driver):
    try:
        btn = driver.find_element(
            By.XPATH,
            "//button[normalize-space(text())='×' or contains(@aria-label,'Close')]"
        )
        btn.click()
        time.sleep(POPUP_PAUSE)
    except NoSuchElementException:
        pass

def extract_product_data(driver, url):
    driver.get(url)
    time.sleep(PAGE_LOAD_PAUSE)
    close_signup_popup(driver)

    data = {
        "url": url,
        "title": "",
        "price": "",
        "description": "",
        "images": []
    }

    # 1) Title
    try:
        data["title"] = driver.find_element(
            By.CSS_SELECTOR,
            "h1[data-component='ProductName'], h1"
        ).text.strip()
    except:
        pass

    # 2) Price
    try:
        data["price"] = driver.find_element(
            By.CSS_SELECTOR,
            "p[data-component='PriceFinalLarge'], p[data-component='PriceCallout']"
        ).text.strip()
    except:
        pass

    # 3) Images
    seen = set()
    for img in driver.find_elements(
        By.CSS_SELECTOR,
        "img[data-component='Img'], div[data-component='Container'] img"
    ):
        src = img.get_attribute("src")
        if src and src not in seen:
            seen.add(src)
            data["images"].append(src)

    # 4) Description: click “The Details” & scrape <p> and <li> from its first two cols
    try:
        # locate & click the “The Details” accordion button
        details_btn = driver.find_element(
            By.XPATH,
            "//p[@data-component='ButtonText' and normalize-space()='The Details']"
            "/ancestor::button"
        )
        if details_btn.get_attribute("data-expanded") == "false":
            details_btn.click()

        # wait until it’s open
        WebDriverWait(driver, 5).until(
            lambda d: details_btn.get_attribute("data-expanded") == "true"
        )
        time.sleep(DETAILS_PAUSE)

        # pull all <p> or <li> from *only* the first two grid columns
        xpath = (
            "//div[@data-component='InnerPanel']/div/div[position()<=2]//p"
            " | //div[@data-component='InnerPanel']/div/div[position()<=2]//li"
        )
        elems = driver.find_elements(By.XPATH, xpath)
        texts = [e.text.strip() for e in elems if e.text.strip()]
        data["description"] = "\n\n".join(texts)

    except Exception:
        # if anything fails here, leave description blank
        pass

    return data

# ─── MAIN LOOP ─────────────────────────────────────────────────────────────────
def main():
    driver = init_driver(headless=HEADLESS)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    input_paths = glob.glob(os.path.join(INPUT_DIR, "*.csv"))

    for in_path in input_paths:
        base = os.path.basename(in_path)
        out_path = os.path.join(OUTPUT_DIR, base)

        # read URLs
        with open(in_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            urls = [
                row["product_url"].strip()
                for row in reader
                if row.get("product_url", "").strip()
            ]

        # write scraped results
        with open(out_path, "w", newline="", encoding="utf-8") as f_out:
            writer = csv.writer(f_out)
            writer.writerow(["Product URL", "Title", "Price", "Description", "Image URLs"])

            for url in urls:
                print("🔍 scraping", url)
                try:
                    item = extract_product_data(driver, url)
                    writer.writerow([
                        item["url"],
                        item["title"],
                        item["price"],
                        item["description"].replace("\n", "  "),
                        ";".join(item["images"])
                    ])
                except Exception as e:
                    print("⚠️ error on", url, e)

    driver.quit()
    print("✅ Done! Scraped CSVs are in", OUTPUT_DIR)

if __name__ == "__main__":
    main()

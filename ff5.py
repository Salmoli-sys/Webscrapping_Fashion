import os
import glob
import csv
import time
import tempfile
import shutil

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ─── CONFIG ────────────────────────────────────────────────────────────────────
INPUT_DIR       = "product_url"      # folder containing your .csv files
OUTPUT_DIR      = "scraped_results"  # folder where scraped CSVs go
HEADLESS        = False
PAGE_LOAD_PAUSE = 3
POPUP_PAUSE     = 1
DETAILS_PAUSE    = 1

FIELDNAMES = ["Product URL", "Title", "Price", "Description", "Image URLs"]

# ─── SETUP ─────────────────────────────────────────────────────────────────────
def init_driver(headless=True):
    opts = Options()
    if headless:
        opts.add_argument("--headless")
        opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    drv = webdriver.Chrome(options=opts)
    drv.implicitly_wait(10)
    return drv

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

    out = {"Product URL": url, "Title": "", "Price": "", "Description": "", "Image URLs": ""}

    # 1) Title (flatten any line breaks)
    try:
        raw_title = driver.find_element(
            By.CSS_SELECTOR,
            "h1[data-component='ProductName'], h1"
        ).text.strip()
        out["Title"] = raw_title.replace("\n", " ")
    except:
        pass

    # 2) Price
    try:
        out["Price"] = driver.find_element(
            By.CSS_SELECTOR,
            "p[data-component='PriceFinalLarge'], p[data-component='PriceCallout']"
        ).text.strip()
    except:
        pass

    # 3) Images
    seen = set()
    imgs = driver.find_elements(
        By.CSS_SELECTOR,
        "img[data-component='Img'], div[data-component='Container'] img"
    )
    urls = []
    for img in imgs:
        src = img.get_attribute("src")
        if src and src not in seen:
            seen.add(src)
            urls.append(src)
    out["Image URLs"] = ";".join(urls)

    # 4) Description
    try:
        btn = driver.find_element(
            By.XPATH,
            "//p[@data-component='ButtonText' and normalize-space()='The Details']"
            "/ancestor::button"
        )
        if btn.get_attribute("data-expanded") == "false":
            btn.click()
        WebDriverWait(driver, 5).until(
            lambda d: btn.get_attribute("data-expanded") == "true"
        )
        time.sleep(DETAILS_PAUSE)

        xpath = (
            "//div[@data-component='InnerPanel']/div/div[position()<=2]//p"
            " | //div[@data-component='InnerPanel']/div/div[position()<=2]//li"
        )
        elems = driver.find_elements(By.XPATH, xpath)
        texts = [e.text.strip() for e in elems if e.text.strip()]
        out["Description"] = "\n\n".join(texts)
    except:
        pass

    # ─── flatten description into one line with pipes
    flat_desc = " | ".join(line for line in out["Description"].splitlines() if line.strip())
    out["Description"] = flat_desc

    return out

def load_existing(output_path):
    data = {}
    if not os.path.isfile(output_path):
        return data
    with open(output_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data[row["Product URL"]] = row
    return data

def write_row_append(output_path, row):
    is_new = not os.path.isfile(output_path)
    with open(output_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if is_new:
            writer.writeheader()
        writer.writerow(row)

def update_row_inplace(output_path, url, new_row):
    temp_fd, temp_path = tempfile.mkstemp(text=True)
    os.close(temp_fd)
    with open(output_path, newline="", encoding="utf-8") as rf, \
         open(temp_path, "w", newline="", encoding="utf-8") as wf:
        reader = csv.DictReader(rf)
        writer = csv.DictWriter(wf, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in reader:
            if row["Product URL"] == url:
                for key in FIELDNAMES[1:]:
                    if not row[key].strip() and new_row[key].strip():
                        row[key] = new_row[key]
            writer.writerow(row)
    shutil.move(temp_path, output_path)

def main():
    driver = init_driver(headless=HEADLESS)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for in_path in glob.glob(os.path.join(INPUT_DIR, "*.csv")):
        base = os.path.basename(in_path)
        out_path = os.path.join(OUTPUT_DIR, base)

        existing = load_existing(out_path)
        with open(in_path, newline="", encoding="utf-8") as rf:
            reader = csv.DictReader(rf)
            urls = [r["product_url"].strip() for r in reader if r.get("product_url")]

        for url in urls:
            row = existing.get(url)
            if row is None:
                print("🔍 scraping (new)  ", url)
                scraped = extract_product_data(driver, url)
                write_row_append(out_path, scraped)
                existing[url] = scraped
            elif any(not row[field].strip() for field in FIELDNAMES[1:]):
                print("🔄 retry scraping ", url)
                scraped = extract_product_data(driver, url)
                update_row_inplace(out_path, url, scraped)
                existing[url].update(scraped)
            else:
                print("✅ already complete", url)

    driver.quit()
    print("✅ All done — outputs in", OUTPUT_DIR)

if __name__ == "__main__":
    main()

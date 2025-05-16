import os
import csv
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ─── CONFIG ────────────────────────────────────────────────────────────────────
INPUT_URLS_CSV  = "product_urls.csv"      # one URL per line, no header
OUTPUT_CSV       = "farfetch_products.csv"
HEADLESS         = False                  # visual mode (set True for a bit more speed)
PAGE_LOAD_PAUSE  = 3                      # seconds to wait after driver.get()
POPUP_PAUSE      = 1                      # pause after closing popup

# ─── SETUP ─────────────────────────────────────────────────────────────────────
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

    data = {"url": url, "title": "", "description": "", "images": []}

    # 1) Title
    try:
        title_el = driver.find_element(
            By.CSS_SELECTOR, "h1[data-component='ProductName'], h1"
        )
        data["title"] = title_el.text.strip()
    except (NoSuchElementException, TimeoutException):
        pass

    # 2) Description = all of “The Details”
    try:
        sec = driver.find_element(
            By.XPATH,
            "//section[@data-component='AccordionItem'][.//p[normalize-space(.)='The Details']]"
        )
        # expand if needed
        if sec.get_attribute("data-expanded") not in ("true", "open"):
            sec.find_element(By.TAG_NAME, "button").click()
            time.sleep(1)
        panel = sec.find_element(By.XPATH, ".//div[@data-component='AccordionPanel']")
        lines = [ln.strip() for ln in panel.text.splitlines() if ln.strip()]
        data["description"] = "; ".join(lines)
    except NoSuchElementException:
        pass

    # desc = ""
    # try:
    #     # wait up to 10s for at least one panel to appear
    #     panels = WebDriverWait(driver, 10).until(
    #         EC.presence_of_all_elements_located(
    #             (By.CSS_SELECTOR, "div[data-component='AccordionPanel']")
    #         )
    #     )
    #     for panel in panels:
    #         txt = panel.text or ""
    #         if "Highlights" in txt:
    #             # split into non‐empty lines, then join with semicolons
    #             lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    #             desc = "; ".join(lines)
    #             break
    # except Exception:
    #     desc = ""

    # data["description"] = desc

    # 3) Images
    seen = set()
    for img in driver.find_elements(
        By.CSS_SELECTOR, "img[data-component='Img'], div[data-component='Container'] img"
    ):
        src = img.get_attribute("src")
        if src and src not in seen:
            seen.add(src)
            data["images"].append(src)

    return data

def main():
    # ensure header
    if not os.path.exists(OUTPUT_CSV):
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f_hdr:
            writer = csv.writer(f_hdr)
            writer.writerow(["Product URL", "Title", "Description", "Image URLs"])

    # load URLs
    with open(INPUT_URLS_CSV, newline="", encoding="utf-8") as f_in:
        urls = [line.strip() for line in f_in if line.strip()]

    driver = init_driver(headless=HEADLESS)

    for url in urls:
        print("🔍 scraping", url)
        try:
            item = extract_product_data(driver, url)
            # append this one row immediately
            with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f_out:
                writer = csv.writer(f_out)
                writer.writerow([
                    item["url"],
                    item["title"],
                    item["description"],
                    "|".join(item["images"])
                ])
        except Exception as e:
            print("⚠️ error on", url, e)

    driver.quit()
    print("✅ Done! Results in", OUTPUT_CSV)

if __name__ == "__main__":
    main()

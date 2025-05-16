import csv
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# ─── CONFIG ────────────────────────────────────────────────────────────────────
INPUT_URLS_CSV  = "product_urls.csv"      # one URL per line, no header
OUTPUT_CSV       = "farfetch_products.csv"
HEADLESS         = False                  # visual mode
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

    data = {
        "url": url,
        "title": "",
        "description": "",
        "images": []
    }

    # 1) Title
    try:
        title_el = driver.find_element(
            By.CSS_SELECTOR,
            "h1[data-component='ProductName'], h1"
        )
        data["title"] = title_el.text.strip()
    except (NoSuchElementException, TimeoutException):
        data["title"] = ""

    # 2) Description = everything under "The Details"
    try:
        # locate the AccordionItem section for "The Details"
        details_section = driver.find_element(
            By.XPATH,
            "//section[@data-component='AccordionItem'][.//p[normalize-space(.)='The Details']]"
        )

        # expand if collapsed
        if details_section.get_attribute("data-expanded") not in ("true", "open"):
            details_section.find_element(By.TAG_NAME, "button").click()
            time.sleep(1)

        # grab the panel text
        panel = details_section.find_element(
            By.XPATH,
            ".//div[@data-component='AccordionPanel']"
        )
        # normalize newlines → semicolons
        lines = [ln.strip() for ln in panel.text.splitlines() if ln.strip()]
        data["description"] = "; ".join(lines)

    except NoSuchElementException:
        data["description"] = ""

    # 3) Images
    imgs = driver.find_elements(
        By.CSS_SELECTOR,
        "img[data-component='Img'], div[data-component='Container'] img"
    )
    seen = set()
    for img in imgs:
        src = img.get_attribute("src")
        if src and src not in seen:
            seen.add(src)
            data["images"].append(src)

    return data

def main():
    driver = init_driver(headless=HEADLESS)

    # read URLs (no header)
    # with open(INPUT_URLS_CSV, newline="", encoding="utf-8") as f:
    #     urls = [line.strip() for line in f if line.strip()]

    with open(INPUT_URLS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        urls = [
            row["product_url"].strip()
            for row in reader
            if row.get("product_url", "").strip()
        ]

    # write output
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["Product URL", "Title", "Description", "Image URLs"])

        for url in urls:
            print("🔍 scraping", url)
            try:
                item = extract_product_data(driver, url)
                writer.writerow([
                    item["url"],
                    item["title"],
                    item["description"],
                    ";".join(item["images"])
                ])
            except Exception as e:
                print("⚠️ error on", url, e)

    driver.quit()
    print("✅ Done! Results in", OUTPUT_CSV)

if __name__ == "__main__":
    main()

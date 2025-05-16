import csv
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC



# ─── CONFIG ────────────────────────────────────────────────────────────────────
INPUT_URLS_CSV  = "product_urls.csv"      # must have header "product_url"
OUTPUT_CSV       = "farfetch_products.csv"
HEADLESS         = False                  # set True for headless
PAGE_LOAD_PAUSE  = 3                      # seconds to wait after driver.get()
POPUP_PAUSE      = 1                      # pause after closing popup
DETAILS_PAUSE     = 1                     # pause after clicking “The Details”

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
        "price": "",
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
    except:
        pass

    # 2) Price
    try:
        price_el = driver.find_element(
            By.CSS_SELECTOR,
            "p[data-component='PriceFinalLarge'], p[data-component='PriceCallout']"
        )
        data["price"] = price_el.text.strip()
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

    # 4) Description: click “The Details” & grab first two grid cells

    # 4) Description: click “The Details”, then scrape all <p> & <li> from the first two columns
    try:
        # 4a) find & click “The Details”
        details_btn = driver.find_element(
            By.XPATH,
            "//p[@data-component='ButtonText' and normalize-space()='The Details']"
            "/ancestor::button"
        )
        if details_btn.get_attribute("data-expanded") == "false":
            details_btn.click()
        # wait until it really flips open
        WebDriverWait(driver, 5).until(
            lambda d: details_btn.get_attribute("data-expanded") == "true"
        )
        time.sleep(DETAILS_PAUSE)

        # 4b) now pull every <p> or <li> under only the first two grid divs:
        xpath = (
            "//div[@data-component='InnerPanel']/div/div[position()<=2]//p"
            " | //div[@data-component='InnerPanel']/div/div[position()<=2]//li"
        )
        elems = driver.find_elements(By.XPATH, xpath)

        # debug—see exactly what we grabbed
        print(f"📝 description elems found: {len(elems)}")
        for i, e in enumerate(elems, 1):
            print(f"    [{i}] » {repr(e.text)}")

        # join non-empty text blocks
        texts = [e.text.strip() for e in elems if e.text.strip()]
        data["description"] = "\n\n".join(texts)

    except Exception as e:
        print(f"⚠️ description error for {url}: {e}")
        # leave blank on failure


    return data


def main():
    driver = init_driver(headless=HEADLESS)

    # read URLs (expects header "product_url")
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
        writer.writerow(["Product URL", "Title", "Price", "Description", "Image URLs"])

        for url in urls:
            print("🔍 scraping", url)
            try:
                item = extract_product_data(driver, url)
                writer.writerow([
                    item["url"],
                    item["title"],
                    item["price"],
                    item["description"].replace("\n", "  "),  # keep it one CSV cell
                    ";".join(item["images"])
                ])
            except Exception as e:
                print("⚠️ error on", url, e)

    driver.quit()
    print("✅ Done! Results in", OUTPUT_CSV)

if __name__ == "__main__":
    main()


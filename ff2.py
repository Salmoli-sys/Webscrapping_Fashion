import csv
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─── CONFIG ────────────────────────────────────────────────────────────────────
INPUT_URLS_CSV   = "product_urls.csv"      # must have header "product_url"
OUTPUT_CSV        = "farfetch_products.csv"
HEADLESS          = False                  # set True for headless
PAGE_LOAD_PAUSE   = 3
POPUP_PAUSE       = 1
DETAILS_PAUSE     = 1
MAX_WORKERS       = 4                      # number of parallel browsers

# ─── SETUP ─────────────────────────────────────────────────────────────────────
def init_driver():
    opts = Options()
    if HEADLESS:
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

    # 4) Description
    try:
        # click “The Details”
        details_btn = driver.find_element(
            By.XPATH,
            "//p[@data-component='ButtonText' and normalize-space()='The Details']"
            "/ancestor::button"
        )
        if details_btn.get_attribute("data-expanded") == "false":
            details_btn.click()
        WebDriverWait(driver, 5).until(
            lambda d: details_btn.get_attribute("data-expanded") == "true"
        )
        time.sleep(DETAILS_PAUSE)

        # grab all <p> & <li> from first two columns
        xpath = (
            "//div[@data-component='InnerPanel']/div/div[position()<=2]//p"
            " | //div[@data-component='InnerPanel']/div/div[position()<=2]//li"
        )
        elems = driver.find_elements(By.XPATH, xpath)
        texts = [e.text.strip() for e in elems if e.text.strip()]
        data["description"] = "\n\n".join(texts)

    except Exception as e:
        print(f"⚠️ description error for {url}: {e}")

    return data

def scrape_single(url):
    driver = init_driver()
    try:
        return extract_product_data(driver, url)
    finally:
        driver.quit()

def main():
    # load URLs
    with open(INPUT_URLS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        urls = [row["product_url"].strip() for row in reader]

    # parallel scrape
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as exec:
        futures = {exec.submit(scrape_single, url): url for url in urls}
        for fut in as_completed(futures):
            url = futures[fut]
            try:
                item = fut.result()
            except Exception as e:
                print(f"⚠️ error scraping {url}: {e}")
                item = {
                    "url": url, "title": "", "price": "",
                    "description": "", "images": []
                }
            results.append(item)

    # write CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["Product URL", "Title", "Price", "Description", "Image URLs"])
        for item in results:
            writer.writerow([
                item["url"],
                item["title"],
                item["price"],
                item["description"].replace("\n", "  "),
                ";".join(item["images"])
            ])

    print("✅ Done! Results in", OUTPUT_CSV)

if __name__ == "__main__":
    main()

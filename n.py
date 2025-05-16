import time
import re
import requests
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

# === CONFIG ===
INPUT_CSV   = "product_urls.csv"
OUTPUT_CSV  = "nakd_product_details.csv"
HEADLESS    = False  # Set True to hide browser

# === Selenium Driver Setup ===
def init_driver(headless=True):
    opts = Options()
    if headless:
        opts.add_argument("--headless")
        opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=opts)
    driver.set_window_size(1920, 1080)
    driver.implicitly_wait(10)
    return driver

# === Scraper Function ===
def scrape_product(driver, url):
    data = {
        "product_url": url,
        "price_with_usd": None,
        "color": None,
        "materials_and_care": {},
        "origin": {}
    }

    # — Selenium for price & color —
    driver.get(url)
    time.sleep(3)

    # Price
    try:
        price_elem = driver.find_element(By.CSS_SELECTOR, "span[itemprop='price']")
        data["price_with_usd"] = "USD " + price_elem.get_attribute("content")
    except NoSuchElementException:
        pass

    # Color
    try:
        color_label = driver.find_element(By.XPATH, "//span[contains(text(), 'Color')]")
        color_value = color_label.find_element(By.XPATH, "./following-sibling::span")
        data["color"] = color_value.text.strip()
    except NoSuchElementException:
        pass

    # — Requests + regex for materials_and_care & origin —
    html = requests.get(url).text

    # Composition
    m = re.search(r'"materialDescription"\s*:\s*"([^"]*)"', html)
    if m:
        data["materials_and_care"]["materialDescription"] = m.group(1)

    # Wash Instructions
    m = re.search(r'"washInstructions"\s*:\s*"([^"]*)"', html)
    if m:
        data["materials_and_care"]["washInstructions"] = m.group(1)

    # Wash Symbols (raw key:value pairs)
    m = re.search(r'"washSymbols"\s*:\s*\{([^}]*)\}', html)
    if m:
        # you can parse this further if needed
        data["materials_and_care"]["washSymbols"] = "{" + m.group(1) + "}"

    # (Optional) Full materialInformationModels block
    m = re.search(r'"materialInformationModels"\s*:\s*(\[[^\]]*\])', html)
    if m:
        data["materials_and_care"]["materialInformationModels"] = m.group(1)

    # Origin: How & where produced
    m = re.search(r'"/ProductBackground/Ingress"\s*:\s*"([^"]*)"', html)
    if m:
        data["origin"]["ProductBackground/Ingress"] = m.group(1)
    m = re.search(r'"/ProductBackground/LocationDescription"\s*:\s*"([^"]*)"', html)
    if m:
        data["origin"]["LocationDescription"] = m.group(1)

    return data

# === Main Runner ===
def main():
    df = pd.read_csv(INPUT_CSV)
    urls = df['product_url'].dropna().unique().tolist()

    driver = init_driver(headless=HEADLESS)

    results = []
    for url in urls:
        try:
            print(f"🔍 Scraping {url}")
            result = scrape_product(driver, url)
            results.append(result)
        except Exception as e:
            print(f"❌ Error at {url}: {e}")

    driver.quit()

    # Build DataFrame and stringify dict columns
    out_df = pd.DataFrame(results)
    out_df["materials_and_care"] = out_df["materials_and_care"].apply(str)
    out_df["origin"] = out_df["origin"].apply(str)
    out_df.to_csv(OUTPUT_CSV, index=False)
    print(f"✅ Done — saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()

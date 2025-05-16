import time
import re
import requests
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# === CONFIG ===
INPUT_CSV   = "product_urls.csv"
OUTPUT_CSV  = "nakd_product_details.csv"
HEADLESS    = False       # True = headless mode
WORKERS     = 4           # number of parallel browser instances

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

# === Single-URL Scrape (price,color + regex for materials/origin) ===
def scrape_product(driver, url):
    data = {
        "product_url": url,
        "price_with_usd": None,
        "color": None,
        "materials_and_care": {},
        "origin": {}
    }

    # Selenium → price & color
    driver.get(url)
    time.sleep(2)
    try:
        price_elem = driver.find_element(By.CSS_SELECTOR, "span[itemprop='price']")
        data["price_with_usd"] = "USD " + price_elem.get_attribute("content")
    except NoSuchElementException:
        pass

    try:
        color_label = driver.find_element(By.XPATH, "//span[contains(text(), 'Color')]")
        color_value = color_label.find_element(By.XPATH, "./following-sibling::span")
        data["color"] = color_value.text.strip()
    except NoSuchElementException:
        pass

    # Requests+regex → materials and origin
    html = requests.get(url).text

    m = re.search(r'"materialDescription"\s*:\s*"([^"]*)"', html)
    if m: data["materials_and_care"]["materialDescription"] = m.group(1)

    m = re.search(r'"washInstructions"\s*:\s*"([^"]*)"', html)
    if m: data["materials_and_care"]["washInstructions"] = m.group(1)

    m = re.search(r'"washSymbols"\s*:\s*\{([^}]*)\}', html)
    if m: data["materials_and_care"]["washSymbols"] = "{" + m.group(1) + "}"

    m = re.search(r'"/ProductBackground/Ingress"\s*:\s*"([^"]*)"', html)
    if m: data["origin"]["Ingress"] = m.group(1)

    m = re.search(r'"/ProductBackground/LocationDescription"\s*:\s*"([^"]*)"', html)
    if m: data["origin"]["LocationDescription"] = m.group(1)

    return data

# === Worker that processes a list of URLs ===
def worker_thread(url_list):
    thread_name = threading.current_thread().name
    driver = init_driver(headless=HEADLESS)
    results = []

    for url in url_list:
        try:
            print(f"[{thread_name}] 🔍 {url}")
            results.append(scrape_product(driver, url))
        except Exception as e:
            print(f"[{thread_name}] ❌ {url} -> {e}")

    driver.quit()
    return results

# === Main: split URLs into N chunks and farm out to threads ===
def main():
    df   = pd.read_csv(INPUT_CSV)
    urls = df['product_url'].dropna().unique().tolist()

    # evenly slice into WORKERS chunks
    chunks = [urls[i::WORKERS] for i in range(WORKERS)]

    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as exe:
        futures = [exe.submit(worker_thread, chunk) for chunk in chunks]
        for fut in as_completed(futures):
            results.extend(fut.result())

    # build output
    out_df = pd.DataFrame(results)
    out_df["materials_and_care"] = out_df["materials_and_care"].apply(str)
    out_df["origin"]               = out_df["origin"].apply(str)
    out_df.to_csv(OUTPUT_CSV, index=False)
    print(f"✅ All done — saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()

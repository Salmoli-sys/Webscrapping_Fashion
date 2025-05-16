import time
import csv
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# === CONFIG ===
INPUT_CSV = "product_urls.csv"
OUTPUT_CSV = "nakd_product_details.csv"
HEADLESS =False

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

def get_text_or_none(driver, by, identifier):
    try:
        return driver.find_element(by, identifier).text.strip()
    except NoSuchElementException:
        return None

# === Scraper Function ===
def scrape_product(driver, url):
    data = {
        "product_url": url,
        "price_with_usd": None,
        "color": None,
        "materials_and_care": {},
        "origin": {}
    }

    driver.get(url)
    time.sleep(3)

    # Price
    try:
        price_elem = driver.find_element(By.CSS_SELECTOR, "span[itemprop='price']")
        data["price_with_usd"] = "USD " + price_elem.get_attribute("content")
    except Exception:
        pass

    # Color
    try:
        color_label = driver.find_element(By.XPATH, "//span[contains(text(), 'Color')]")
        color_value = color_label.find_element(By.XPATH, "./following-sibling::span")
        data["color"] = color_value.text.strip()
    except Exception:
        pass

    # Open "Materials and care" tab
    try:
        materials_tab = driver.find_element(By.XPATH, "//button[contains(text(), 'Materials and care')]")
        materials_tab.click()
        time.sleep(1)

        mat_section = driver.find_element(By.XPATH, "//div[contains(@class, 'q7.qau.qq.qhf')]")
        sections = mat_section.find_elements(By.XPATH, ".//div[contains(@class, 'q7')]")
        for section in sections:
            try:
                key = section.find_element(By.XPATH, ".//div[contains(@class, 'q7')]").text.strip().replace(":", "")
                val = section.find_element(By.XPATH, ".//div[contains(@class, 'q7')][2]").text.strip()
                data["materials_and_care"][key] = val
            except:
                continue
    except Exception:
        pass

    # Open "Origin" tab
    try:
        origin_tab = driver.find_element(By.XPATH, "//button[contains(text(), 'Origin')]")
        origin_tab.click()
        time.sleep(1)

        origin_section = driver.find_element(By.XPATH, "//div[contains(text(), 'Where & how is it produced?')]/..")
        all_ps = origin_section.find_elements(By.TAG_NAME, "p")
        if all_ps:
            data["origin"]["Where & how is it produced?"] = all_ps[0].text.strip()
        if len(all_ps) > 1:
            data["origin"]["This product has been made in one of the following countries:"] = all_ps[1].text.strip()
    except Exception:
        pass

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
            data = scrape_product(driver, url)
            results.append(data)
        except Exception as e:
            print(f"❌ Error scraping {url}: {e}")
            continue

    driver.quit()

    # Convert to DataFrame
    out_df = pd.DataFrame(results)
    out_df["materials_and_care"] = out_df["materials_and_care"].apply(lambda x: str(x))
    out_df["origin"] = out_df["origin"].apply(lambda x: str(x))
    out_df.to_csv(OUTPUT_CSV, index=False)
    print(f"✅ Done. Data saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()

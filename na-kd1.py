import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# === CONFIG ===
INPUT_CSV      = "product_urls.csv"
OUTPUT_CSV     = "nakd_product_details.csv"
PAGE_LOAD_PAUSE = 2.0
CLICK_PAUSE     = 1.0

def init_driver():
    opts = Options()
    # no --headless → visible browser
    opts.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(10)
    return driver

def click_by_text(driver, text):
    """
    Find any element whose exact text matches `text`,
    scroll it into view, and JS-click it.
    Returns True if click succeeded.
    """
    xpath = f"//*[normalize-space(text())='{text}']"
    elems = driver.find_elements(By.XPATH, xpath)
    for e in elems:
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", e)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", e)
            return True
        except Exception:
            continue
    return False

def parse_panel_text(panel):
    """
    Given a WebElement `panel`, split its innerText into lines,
    group lines under headings ending with ':'.
    """
    text = panel.get_attribute("innerText") or ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    sections = {}
    key = None
    for ln in lines:
        if ln.endswith(":"):
            key = ln[:-1]
            sections[key] = []
        elif key:
            sections[key].append(ln)
    return {k: "\n".join(v) for k, v in sections.items()}

def scrape_product(driver, url):
    data = {
        "product_url": url,
        "price_with_usd": None,
        "color": None,
        "materials_and_care": {},
        "origin": {},
    }

    driver.get(url)
    time.sleep(PAGE_LOAD_PAUSE)

    # — Price
    try:
        el = driver.find_element(By.CSS_SELECTOR, "span[itemprop='price']")
        data["price_with_usd"] = f"USD {el.get_attribute('content')}"
    except:
        pass

    # — Color
    try:
        lbl = driver.find_element(By.XPATH, "//span[contains(text(),'Color')]")
        val = lbl.find_element(By.XPATH, "./following-sibling::span")
        data["color"] = val.text.strip()
    except:
        pass

    # — Open overlay by clicking "Materials and care" on page
    if not click_by_text(driver, "Materials and care"):
        return data
    time.sleep(CLICK_PAUSE)

    # — Grab the overlay container (role="dialog")
    try:
        panel = driver.find_element(By.CSS_SELECTOR, "div[role='dialog']")
    except:
        return data

    # — Parse default tab (Materials and care)
    mats = parse_panel_text(panel)
    data["materials_and_care"] = mats

    # — Switch to Origin tab
    if click_by_text(driver, "Origin"):
        time.sleep(CLICK_PAUSE)
        panel = driver.find_element(By.CSS_SELECTOR, "div[role='dialog']")
        org = parse_panel_text(panel)
        data["origin"] = org

    # — Close the overlay
    click_by_text(driver, "Close") or click_by_text(driver, "×")
    time.sleep(0.5)

    return data

def main():
    df_urls = pd.read_csv(INPUT_CSV)
    urls = df_urls["product_url"].dropna().unique().tolist()

    driver = init_driver()
    records = []

    for url in urls:
        print("🔍 Scraping", url)
        try:
            rec = scrape_product(driver, url)
            records.append(rec)
        except Exception as e:
            print("  ❌ Error:", e)

    driver.quit()

    # Ensure columns even if no records
    cols = ["product_url","price_with_usd","color","materials_and_care","origin"]
    df_out = pd.DataFrame(records, columns=cols)

    # Convert dicts → strings for CSV
    df_out["materials_and_care"] = df_out["materials_and_care"].apply(str)
    df_out["origin"]              = df_out["origin"].apply(str)

    df_out.to_csv(OUTPUT_CSV, index=False)
    print("✅ Saved to", OUTPUT_CSV)

if __name__ == "__main__":
    main()

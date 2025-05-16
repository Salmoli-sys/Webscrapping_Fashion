import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# === CONFIG ===
INPUT_CSV       = "product_urls.csv"
OUTPUT_CSV      = "nakd_product_details.csv"
PAGE_LOAD_PAUSE = 2.0
CLICK_PAUSE     = 1.0
WAIT_TIMEOUT    = 10

def init_driver():
    opts = Options()
    opts.add_argument("--start-maximized")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(5)
    # hide webdriver flag
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get:() => undefined});"}
    )
    return driver

def real_click(driver, el):
    ActionChains(driver).move_to_element(el).pause(0.2).click().perform()
    time.sleep(CLICK_PAUSE)

def open_accordion_panel(driver, identifier):
    """
    Click the <button data-identifier="{identifier}">,
    then return the first following-sibling <div> that
    is visible and has non-empty text.
    """
    # 1) click the correct tab button
    btn = WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, f"button[data-identifier='{identifier}']"))
    )
    real_click(driver, btn)

    # 2) find its wrapper <div> and all of its sibling <div>s
    wrapper = btn.find_element(By.XPATH, "./parent::*")
    # wait until at least one sibling <div> has text
    WebDriverWait(driver, WAIT_TIMEOUT).until(
        lambda d: any(
            sib.text.strip() and sib.is_displayed()
            for sib in wrapper.find_elements(By.XPATH, "following-sibling::div")
        )
    )

    # 3) grab the first visible, non-empty sibling
    for sib in wrapper.find_elements(By.XPATH, "following-sibling::div"):
        if sib.is_displayed() and sib.text.strip():
            driver.execute_script("arguments[0].scrollIntoView(true);", sib)
            time.sleep(0.2)
            return sib

    raise RuntimeError(f"No accordion panel found for '{identifier}'")

def parse_panel_text(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    out, key = {}, None
    for l in lines:
        if l.endswith(":"):
            key = l[:-1]
            out[key] = []
        elif key:
            out[key].append(l)
    return {k: "\n".join(v) for k, v in out.items()}

def scrape_product(driver, url):
    rec = {
        "product_url": url,
        "price_with_usd": None,
        "color": None,
        "materials_and_care": {},
        "origin": {},
    }

    driver.get(url)
    time.sleep(PAGE_LOAD_PAUSE)

    # close pop-up if any
    try:
        close_btn = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Close']")
        real_click(driver, close_btn)
    except:
        pass

    # price
    try:
        price_el = driver.find_element(By.CSS_SELECTOR, "span[itemprop='price']")
        rec["price_with_usd"] = "USD " + price_el.get_attribute("content")
    except:
        pass

    # color
    try:
        lbl = driver.find_element(By.XPATH, "//span[contains(text(),'Color')]")
        rec["color"] = lbl.find_element(By.XPATH, "./following-sibling::span").text.strip()
    except:
        pass

    # Materials and care
    try:
        panel = open_accordion_panel(driver, "materials-care")
        rec["materials_and_care"] = parse_panel_text(panel.text)
    except Exception as e:
        print("  ! materials error:", e)

    # Origin
    try:
        panel = open_accordion_panel(driver, "origin")
        rec["origin"] = parse_panel_text(panel.text)
    except Exception as e:
        print("  ! origin error:", e)

    return rec

def main():
    df = pd.read_csv(INPUT_CSV)
    urls = df["product_url"].dropna().unique().tolist()
    driver = init_driver()
    results = []

    for url in urls:
        print("🔍", url)
        try:
            results.append(scrape_product(driver, url))
        except Exception as e:
            print("  ❌ failed:", e)

    driver.quit()

    df_out = pd.DataFrame(results)
    for col in ("materials_and_care", "origin"):
        if col not in df_out:
            df_out[col] = "{}"
    df_out["materials_and_care"] = df_out["materials_and_care"].astype(str)
    df_out["origin"]              = df_out["origin"].astype(str)
    df_out.to_csv(OUTPUT_CSV, index=False)
    print("✅ Saved to", OUTPUT_CSV)

if __name__ == "__main__":
    main()
#running except origin
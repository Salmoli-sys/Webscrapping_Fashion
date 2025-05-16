import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

# === CONFIG ===
INPUT_CSV       = "product_urls.csv"
OUTPUT_CSV      = "nakd_product_details.csv"
PAGE_LOAD_PAUSE = 2.0
CLICK_PAUSE     = 1.0
SCROLL_STEPS    = 8      # how many times to page-down inside the overlay

def init_driver():
    opts = Options()
    # run visibly
    opts.add_argument("--start-maximized")
    # hide the “automation” flag
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(10)
    # override navigator.webdriver
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
              Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """
        },
    )
    return driver

def real_click(driver, element):
    """Move, hover, and click via ActionChains."""
    ActionChains(driver).move_to_element(element).pause(0.2).click().perform()
    time.sleep(0.5)

def open_overlay(driver, link_text):
    """
    Click the link that reads link_text (e.g. 'Materials and care'),
    then focus the overlay and scroll it down.
    """
    # 1) find and real-click the button on the main page
    btn = driver.find_element(By.XPATH, f"//*[normalize-space()='{link_text}']")
    real_click(driver, btn)

    # 2) wait a sec then find the dialog
    time.sleep(CLICK_PAUSE)
    dialog = driver.find_element(By.CSS_SELECTOR, "div[role='dialog']")
    # 3) click inside it to focus
    real_click(driver, dialog)

    # 4) page-down inside the overlay to lazy-render content
    for _ in range(SCROLL_STEPS):
        dialog.send_keys(Keys.PAGE_DOWN)
        time.sleep(0.2)

    return dialog

def parse_panel_text(text):
    """
    Given innerText of a panel, group lines under headings ending with ':'.
    """
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
    record = {
        "product_url": url,
        "price_with_usd": None,
        "color": None,
        "materials_and_care": {},
        "origin": {},
    }

    driver.get(url)
    time.sleep(PAGE_LOAD_PAUSE)

    # close newsletter banner if there
    try:
        close_btn = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Close']")
        real_click(driver, close_btn)
    except:
        pass

    # price
    try:
        el = driver.find_element(By.CSS_SELECTOR, "span[itemprop='price']")
        record["price_with_usd"] = "USD " + el.get_attribute("content")
    except:
        pass

    # color
    try:
        lbl = driver.find_element(By.XPATH, "//span[contains(text(),'Color')]")
        val = lbl.find_element(By.XPATH, "./following-sibling::span")
        record["color"] = val.text.strip()
    except:
        pass

    # Materials and care
    try:
        dialog = open_overlay(driver, "Materials and care")
        text = dialog.get_attribute("innerText") or ""
        record["materials_and_care"] = parse_panel_text(text)
    except Exception as e:
        print("  ! materials error:", e)

    # Origin tab
    try:
        origin_btn = driver.find_element(By.XPATH, "//button[normalize-space()='Origin']")
        real_click(driver, origin_btn)
        # scroll back up then down to ensure fresh render
        dialog = driver.find_element(By.CSS_SELECTOR, "div[role='dialog']")
        dialog.send_keys(Keys.HOME)
        time.sleep(0.3)
        for _ in range(SCROLL_STEPS):
            dialog.send_keys(Keys.PAGE_DOWN)
            time.sleep(0.2)

        text = dialog.get_attribute("innerText") or ""
        record["origin"] = parse_panel_text(text)
    except Exception as e:
        print("  ! origin error:", e)

    # close overlay
    try:
        x = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Close']")
        real_click(driver, x)
    except:
        pass

    return record

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

    # ensure columns exist
    df_out = pd.DataFrame(results)
    for col in ("materials_and_care","origin"):
        if col not in df_out:
            df_out[col] = "{}"

    # stringify dicts
    df_out["materials_and_care"] = df_out["materials_and_care"].apply(str)
    df_out["origin"]              = df_out["origin"].apply(str)
    df_out.to_csv(OUTPUT_CSV, index=False)
    print("✅ Done →", OUTPUT_CSV)

if __name__ == "__main__":
    main()
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
SCROLL_STEPS    = 8

def init_driver():
    opts = Options()
    opts.add_argument("--start-maximized")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(10)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
              Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """
        },
    )
    return driver

def real_click(driver, el):
    ActionChains(driver).move_to_element(el).pause(0.2).click().perform()
    time.sleep(0.5)

def open_overlay(driver, link_text):
    btn = driver.find_element(By.XPATH, f"//*[normalize-space()='{link_text}']")
    real_click(driver, btn)
    time.sleep(CLICK_PAUSE)

    # focus the <div role="tabpanel"> panel so we can send keys to it
    panels = driver.find_elements(By.CSS_SELECTOR, "div[role='tabpanel']")
    for p in panels:
        if p.is_displayed():
            panel = p
            break
    else:
        raise RuntimeError("No tabpanel found")

    # scroll *that* panel
    for _ in range(SCROLL_STEPS):
        panel.send_keys(Keys.PAGE_DOWN)
        time.sleep(0.2)

    return panel

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

    # close newsletter
    try:
        x = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Close']")
        real_click(driver, x)
    except:
        pass

    # price
    try:
        el = driver.find_element(By.CSS_SELECTOR, "span[itemprop='price']")
        rec["price_with_usd"] = "USD " + el.get_attribute("content")
    except:
        pass

    # color
    try:
        lbl = driver.find_element(By.XPATH, "//span[contains(text(),'Color')]")
        val = lbl.find_element(By.XPATH, "./following-sibling::span")
        rec["color"] = val.text.strip()
    except:
        pass

    # Materials and care
    try:
        mat_panel = open_overlay(driver, "Materials and care")
        rec["materials_and_care"] = parse_panel_text(mat_panel.text)
    except Exception as e:
        print("  ! materials error:", e)

    # Origin
    try:
        origin_btn = driver.find_element(By.XPATH, "//button[normalize-space()='Origin']")
        real_click(driver, origin_btn)
        time.sleep(CLICK_PAUSE)

        # grab the new visible panel
        panels = driver.find_elements(By.CSS_SELECTOR, "div[role='tabpanel']")
        for p in panels:
            if p.is_displayed():
                origin_panel = p
                break
        # scroll it again
        origin_panel.send_keys(Keys.HOME)
        time.sleep(0.3)
        for _ in range(SCROLL_STEPS):
            origin_panel.send_keys(Keys.PAGE_DOWN)
            time.sleep(0.2)

        rec["origin"] = parse_panel_text(origin_panel.text)
    except Exception as e:
        print("  ! origin error:", e)

    # close overlay
    try:
        x = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Close']")
        real_click(driver, x)
    except:
        pass

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
    df_out["materials_and_care"] = df_out["materials_and_care"].apply(str)
    df_out["origin"]              = df_out["origin"].apply(str)
    df_out.to_csv(OUTPUT_CSV, index=False)
    print("✅ Saved to", OUTPUT_CSV)

if __name__ == "__main__":
    main()

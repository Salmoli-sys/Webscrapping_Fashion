import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# === CONFIG ===
INPUT_CSV = "product_urls.csv"
OUTPUT_CSV = "nakd_product_details.csv"
PAGE_LOAD_PAUSE = 2.0
CLICK_PAUSE = 1.0
WAIT_TIMEOUT = 10


def init_driver():
    """Initialize Selenium WebDriver with Chrome options."""
    options = Options()
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(5)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get:() => undefined});"},
    )
    return driver


def real_click(driver, element):
    """Perform a reliable click via ActionChains and pause."""
    ActionChains(driver).move_to_element(element).pause(0.2).click().perform()
    time.sleep(CLICK_PAUSE)


def close_popup(driver):
    """Close any pop-up dialog if it appears."""
    try:
        btn = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Close']"))
        )
        real_click(driver, btn)
    except Exception:
        pass


def extract_accordion_section(driver, identifier):
    """
    Click the accordion button and parse its panel content.
    Supports selectors by data-id, id, or data-identifier.
    Returns a dict of headers -> values.
    """
    # locate and click the button
    selector = f"button[data-id='{identifier}'], button[id='{identifier}'], button[data-identifier='{identifier}']"
    btn = WebDriverWait(driver, WAIT_TIMEOUT).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
    )
    real_click(driver, btn)

    # wait for panel sibling to appear
    wrapper = btn.find_element(By.XPATH, "./parent::*")
    WebDriverWait(driver, WAIT_TIMEOUT).until(
        lambda d: any(
            sib.is_displayed() and sib.text.strip()
            for sib in wrapper.find_elements(By.XPATH, "following-sibling::div")
        )
    )

    # gather all visible siblings
    siblings = wrapper.find_elements(By.XPATH, "following-sibling::div")
    sections = {}

    for sib in siblings:
        if not sib.is_displayed() or not sib.text.strip():
            continue
        text = sib.text.strip()
        # parse colon-based sub-sections
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        # if any line ends with ':' use parse_panel_text
        if any(line.endswith(":") for line in lines):
            panel = parse_panel_text(text)
            sections.update(panel)
        else:
            # first line as header, rest join as value
            header = lines[0]
            value = "\n".join(lines[1:]) if len(lines) > 1 else ""
            sections[header] = value

    return sections


def parse_panel_text(text):
    """
    Convert colon-delimited blocks into a dict.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    data = {}
    key = None
    for line in lines:
        if line.endswith(":"):
            key = line[:-1]
            data[key] = []
        elif key:
            data[key].append(line)
    return {header: "\n".join(items) for header, items in data.items()}


def scrape_product(driver, url):
    """
    Visit url and scrape price, color, materials & care, and origin.
    """
    record = {
        "product_url": url,
        "price_with_usd": None,
        "color": None,
        "materials_and_care": {},
        "origin": {},
    }

    driver.get(url)
    time.sleep(PAGE_LOAD_PAUSE)
    close_popup(driver)

    # price
    try:
        el = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "span[itemprop='price']"))
        )
        record["price_with_usd"] = f"USD {el.get_attribute('content')}"
    except Exception:
        print("  ! price error")

    # color
    try:
        lbl = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(),'Color')]") )
        )
        record["color"] = lbl.find_element(By.XPATH, "./following-sibling::span").text.strip()
    except Exception:
        print("  ! color error")

    # panels
    try:
        record["materials_and_care"] = extract_accordion_section(driver, "materials-care")
    except Exception as e:
        print("  ! materials error:", e)
    try:
        record["origin"] = extract_accordion_section(driver, "origin")
    except Exception as e:
        print("  ! origin error:", e)

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

    # save results
    out = pd.DataFrame(results)
    for col in ("materials_and_care", "origin"):
        if col not in out:
            out[col] = "{}"
    out["materials_and_care"] = out["materials_and_care"].astype(str)
    out["origin"] = out["origin"].astype(str)
    out.to_csv(OUTPUT_CSV, index=False)
    print("✅ Saved to", OUTPUT_CSV)


if __name__ == "__main__":
    main()

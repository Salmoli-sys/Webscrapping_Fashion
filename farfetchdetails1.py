import csv
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ─── CONFIG ────────────────────────────────────────────────────────────────────
INPUT_URLS_CSV  = "product_urls.csv"      # one URL per line, no header
OUTPUT_CSV       = "farfetch_products.csv"
HEADLESS         = False                  # visual mode
PAGE_LOAD_PAUSE  = 3                      # after driver.get()
POPUP_PAUSE      = 1                      # after closing popup
DETAILS_TIMEOUT  = 5                      # seconds to wait for panel

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

    data = {"url": url, "title": "", "description": "", "images": []}

    # 1) Title
    try:
        h1 = driver.find_element(By.CSS_SELECTOR, "h1[data-component='ProductName'], h1")
        data["title"] = h1.text.strip()
    except (NoSuchElementException, TimeoutException):
        pass

    # 2) “The Details” accordion
    try:
        # locate the <section> that wraps “The Details”
        section = driver.find_element(
            By.XPATH,
            "//section[@data-component='AccordionItem'][.//p[normalize-space(.)='The Details']]"
        )
        btn = section.find_element(By.CSS_SELECTOR, "button[data-component='AccordionButton']")
        panel = section.find_element(By.CSS_SELECTOR, "div[data-component='AccordionPanel']")

        # only click if panel is not already visible
        if not panel.is_displayed():
            # scroll into center so it isn't under the sticky header
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                btn
            )
            time.sleep(0.3)
            # JS click to avoid interception
            driver.execute_script("arguments[0].click();", btn)

            # wait for it to be visible
            WebDriverWait(section, DETAILS_TIMEOUT).until(
                EC.visibility_of(panel)
            )

        # now grab every non-blank line
        lines = [ln.strip() for ln in panel.text.splitlines() if ln.strip()]
        data["description"] = "; ".join(lines)

    except (NoSuchElementException, TimeoutException):
        data["description"] = ""

    # 3) Images
    imgs = driver.find_elements(
        By.CSS_SELECTOR,
        "img[data-component='Img'], div[data-component='Container'] img"
    )
    seen = set()
    for img in imgs:
        src = img.get_attribute("src")
        if src and src not in seen:
            seen.add(src)
            data["images"].append(src)

    return data

def main():
    driver = init_driver(headless=HEADLESS)

    # load URLs
    with open(INPUT_URLS_CSV, newline="", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    # scrape & write
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as out:
        writer = csv.writer(out)
        writer.writerow(["Product URL", "Title", "Description", "Image URLs"])
        for url in urls:
            print("🔍 scraping", url)
            try:
                item = extract_product_data(driver, url)
                writer.writerow([
                    item["url"],
                    item["title"],
                    item["description"],
                    "|".join(item["images"])
                ])
            except Exception as e:
                print("⚠️ error on", url, e)

    driver.quit()
    print("✅ Done! See", OUTPUT_CSV)

if __name__ == "__main__":
    main()

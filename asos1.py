import time
import re
import csv
import pathlib
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

def sanitize_filename(name: str) -> str:
    # turn "Dresses & Skirts" → "dresses_skirts"
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')

def extract_subcategories(driver, section_url):
    driver.get(section_url)
    time.sleep(3)

    # 1) click the “Clothing” tab in the top bar
    buttons = driver.find_elements(By.CSS_SELECTOR, 'button[data-testid="primarynav-button"]')
    for btn in buttons:
        if btn.text.strip().lower() == "clothing":
            btn.click()
            break
    else:
        raise RuntimeError("Could not find the Clothing button")
    time.sleep(3)

    clothing_base = driver.current_url.rstrip('/')  # e.g. https://www.asos.com/women/clothing

    # 2) grab all sub-category anchors that live under /clothing/…/cat/
    subcats = []
    anchors = driver.find_elements(By.CSS_SELECTOR, f'a[href^="{clothing_base}"]')
    seen = set()
    for a in anchors:
        href = a.get_attribute("href")
        text = a.text.strip()
        if not text or "cat" not in href:
            continue
        if href in seen:
            continue
        seen.add(href)
        subcats.append((text, href))
    return subcats

def scrape_category(driver, subcat_name, subcat_url, section_name, visual=True):
    driver.get(subcat_url)
    time.sleep(3)

    # keep clicking “LOAD MORE” until it disappears
    while True:
        try:
            load_more = driver.find_element(
                By.XPATH, "//button[normalize-space()='LOAD MORE' or normalize-space()='Load more']"
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", load_more)
            time.sleep(0.5)
            load_more.click()
            time.sleep(2)
        except NoSuchElementException:
            break

    # one final scroll to flush any lazy‐loaded items
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    # grab every <a href> with /prd/ + at least 5 digits
    urls = set()
    for a in driver.find_elements(By.CSS_SELECTOR, 'a[href*="/prd/"]'):
        href = a.get_attribute("href")
        if re.search(r"/prd/\d{5,}", href):
            urls.add(href)

    # write CSV
    fname = f"{section_name}_{sanitize_filename(subcat_name)}.csv"
    pathlib.Path(fname).parent.mkdir(parents=True, exist_ok=True)
    with open(fname, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["product_url"])
        for url in sorted(urls):
            writer.writerow([url])

    print(f"[{section_name.upper()}] {subcat_name}: {len(urls)} URLs → {fname}")

if __name__ == "__main__":
    visual = True  # set False for headless
    opts = Options()
    if not visual:
        opts.add_argument("--headless")
        opts.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=opts)

    try:
        for section_name, section_url in [
            ("women", "https://www.asos.com/women/"),
            ("men",   "https://www.asos.com/men/")
        ]:
            print(f"\n→ Extracting sub-categories for {section_name.upper()} …")
            subcats = extract_subcategories(driver, section_url)
            for name, url in subcats:
                scrape_category(driver, name, url, section_name, visual)

    finally:
        driver.quit()

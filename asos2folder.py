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

    # 2) grab all sub-category anchors under /clothing/.../cat/
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

def scrape_category(driver, subcat_name, subcat_url, section_name):
    driver.get(subcat_url)
    time.sleep(3)

    # keep clicking “Load more” until all products are loaded
    while True:
        try:
            counter_el = driver.find_element(
                By.XPATH,
                "//p[contains(., \"You've viewed\") or contains(., 'You’ve viewed')]"
            )
            m = re.search(r"([\d,]+)\s+of\s+([\d,]+)\s+products", counter_el.text)
            loaded, total = map(lambda s: int(s.replace(",", "")), m.groups())
        except Exception:
            loaded, total = 0, 1

        print(f" → loaded {loaded}/{total}")
        if loaded >= total:
            break

        try:
            loader = driver.find_element(
                By.XPATH,
                (
                  "//button[normalize-space()='LOAD MORE' or normalize-space()='Load more']"
                  " | "
                  "//a[normalize-space()='LOAD MORE' or normalize-space()='Load more']"
                )
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", loader)
            time.sleep(0.5)
            loader.click()
            time.sleep(2)
        except NoSuchElementException:
            break

    # final scroll to flush lazy-loaded items
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    # collect product links
    urls = {
        a.get_attribute("href")
        for a in driver.find_elements(By.CSS_SELECTOR, 'a[href*="/prd/"]')
        if re.search(r"/prd/\d{5,}", a.get_attribute("href"))
    }

    # prepare output directory and filename
    output_dir = pathlib.Path(section_name)
    output_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{section_name}_{sanitize_filename(subcat_name)}.csv"
    file_path = output_dir / fname

    # write CSV
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["product_url"])
        for url in sorted(urls):
            writer.writerow([url])

    print(f"[{section_name.upper()}] {subcat_name}: {len(urls)} URLs → {file_path}")

if __name__ == "__main__":
    # toggle visual=False for headless mode
    visual = True
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
                scrape_category(driver, name, url, section_name)
    finally:
        driver.quit()

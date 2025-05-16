import time
import re
import csv
import pathlib
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

def sanitize_filename(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')

def extract_subcategories(driver, section_url):
    driver.get(section_url)
    time.sleep(3)

    # click the “Clothing” tab
    buttons = driver.find_elements(By.CSS_SELECTOR, 'button[data-testid="primarynav-button"]')
    for btn in buttons:
        if btn.text.strip().lower() == "clothing":
            btn.click()
            break
    else:
        raise RuntimeError("Could not find the Clothing button")
    time.sleep(3)

    base = driver.current_url.rstrip('/')
    seen = set()
    subcats = []
    for a in driver.find_elements(By.CSS_SELECTOR, f'a[href^="{base}"]'):
        href = a.get_attribute("href")
        text = a.text.strip()
        if not text or "cat" not in href or href in seen:
            continue
        seen.add(href)
        subcats.append((text, href))
    return subcats

def scrape_category(subcat_name, subcat_url, section_name, chrome_opts):
    # — NEW DRIVER PER SUB-CATEGORY —
    driver = webdriver.Chrome(options=chrome_opts)
    try:
        driver.get(subcat_url)
        time.sleep(3)

        # click "Load more" until all are loaded
        while True:
            try:
                p = driver.find_element(
                    By.XPATH,
                    "//p[contains(., \"You've viewed\") or contains(., 'You’ve viewed')]"
                )
                loaded, total = map(
                    lambda s: int(s.replace(",", "")),
                    re.search(r"([\d,]+)\s+of\s+([\d,]+)\s+products", p.text).groups()
                )
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

        # final scroll to load lazy items
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        # collect product URLs
        urls = {
            a.get_attribute("href")
            for a in driver.find_elements(By.CSS_SELECTOR, 'a[href*="/prd/"]')
            if re.search(r"/prd/\d{5,}", a.get_attribute("href"))
        }

        # ensure section folder exists (women/ or men/)
        output_dir = pathlib.Path(section_name)
        output_dir.mkdir(parents=True, exist_ok=True)

        # write CSV inside that folder
        fname = f"{section_name}_{sanitize_filename(subcat_name)}.csv"
        file_path = output_dir / fname
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["product_url"])
            for url in sorted(urls):
                writer.writerow([url])

        print(f"[{section_name.upper()}] {subcat_name}: {len(urls)} URLs → {file_path}")

    finally:
        driver.quit()  # ← quit this driver before returning

if __name__ == "__main__":
    visual = True
    chrome_opts = Options()
    if not visual:
        chrome_opts.add_argument("--headless")
        chrome_opts.add_argument("--disable-gpu")

    # one master driver just to list sub-categories
    master = webdriver.Chrome(options=chrome_opts)
    try:
        for section_name, section_url in [
            ("women", "https://www.asos.com/women/"),
            ("men",   "https://www.asos.com/men/")
        ]:
            print(f"\n→ Extracting sub-categories for {section_name.upper()} …")
            subcats = extract_subcategories(master, section_url)

            # for each sub-category: open new driver, scrape, then quit it
            for subcat_name, subcat_url in subcats:
                scrape_category(subcat_name, subcat_url, section_name, chrome_opts)

    finally:
        master.quit()

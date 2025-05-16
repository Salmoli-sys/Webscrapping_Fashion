import time
import re
import csv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

def get_clothing_urls(section_url, section_name, visual=True):
    # ─── Setup WebDriver ───────────────────────────────────────
    opts = Options()
    if not visual:
        opts.add_argument("--headless")
        opts.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=opts)

    try:
        driver.get(section_url)
        time.sleep(3)

        # ─── 1) Click the “Clothing” tab ───────────────────────────
        buttons = driver.find_elements(By.CSS_SELECTOR, 'button[data-testid="primarynav-button"]')
        for btn in buttons:
            if btn.text.strip().lower() == "clothing":
                btn.click()
                break
        else:
            raise RuntimeError(f"'Clothing' tab not found on {section_url}")
        time.sleep(3)

        # ─── 2) Repeatedly click LOAD MORE ──────────────────────────
        while True:
            try:
                load_more = driver.find_element(
                    By.XPATH,
                    "//button[normalize-space()='LOAD MORE' or normalize-space()='Load more']"
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", load_more)
                time.sleep(0.5)
                load_more.click()
                time.sleep(2)
            except NoSuchElementException:
                break

        # ─── 3) Final scroll to flush in-DOM lazy content ───────────
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        # ─── 4) Grab all /prd/ URLs with 5+ digit IDs ───────────────
        urls = set()
        for a in driver.find_elements(By.CSS_SELECTOR, 'a[href*="/prd/"]'):
            href = a.get_attribute("href")
            if re.search(r"/prd/\d{5,}", href):
                urls.add(href)

    finally:
        driver.quit()

    # ─── 5) Dump to CSV ──────────────────────────────────────────
    filename = f"{section_name.lower()}_clothing_urls.csv"
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["product_url"])
        for u in sorted(urls):
            writer.writerow([u])
    print(f"→ {len(urls)} URLs written to {filename}")

    return urls

if __name__ == "__main__":
    women_url = "https://www.asos.com/women/"
    men_url   = "https://www.asos.com/men/"

    print("Scraping WOMEN → Clothing …")
    get_clothing_urls(women_url, "women", visual=True)

    print("Scraping MEN → Clothing …")
    get_clothing_urls(men_url, "men", visual=True)

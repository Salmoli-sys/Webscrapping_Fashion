import os
import time
import csv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def init_driver(headless=True, profile_dir=None):
    opts = Options()
    if headless:
        opts.add_argument("--headless")
        opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    if profile_dir:
        opts.add_argument(f"user-data-dir={profile_dir}")
    driver = webdriver.Chrome(options=opts)
    driver.set_window_size(1920, 1080)
    driver.implicitly_wait(10)
    return driver

def close_signup_popup(driver, pause=1):
    try:
        btn = driver.find_element(
            By.XPATH,
            "//button[normalize-space(text())='×' or contains(@aria-label, 'Close')]"
        )
        btn.click()
        time.sleep(pause)
    except Exception:
        pass

def load_all_products(driver, pause=1):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(pause)

def scrape_women_clothing(last_page=1654, headless=True, profile_dir=None):
    base_url = "https://www.farfetch.com/in/shopping/men/clothing-2/items.aspx"
    all_urls = set()
    out_file = "men.csv"

    # Open CSV and write header
    with open(out_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["product_url"])
        csvfile.flush()

        # Loop through pages
        for page in range(1, last_page + 1):
            url = f"{base_url}?page={page}"
            print(f"\n→ Page {page}/{last_page}: {url}")

            driver = init_driver(headless=headless, profile_dir=profile_dir)
            # Suppress newsletter popup
            driver.get("https://www.farfetch.com")
            driver.execute_script(
                "window.localStorage.setItem('newsletter_popup_shown','true');"
            )

            driver.get(url)
            time.sleep(2)
            close_signup_popup(driver)
            load_all_products(driver)

            # Scrape this page
            page_urls = set()
            items = driver.find_elements(
                By.CSS_SELECTOR, "a[href*='/shopping/'][href$='.aspx']"
            )
            for itm in items:
                href = itm.get_attribute("href")
                if href and "items.aspx" not in href:
                    page_urls.add(href)
            driver.quit()

            # Dedupe against all_urls
            new_urls = page_urls - all_urls
            all_urls.update(new_urls)

            # Append new URLs to CSV
            for link in sorted(new_urls):
                writer.writerow([link])
            csvfile.flush()

            print(f"  • Found {len(page_urls)} URLs on page, {len(new_urls)} new appended")
    
    print(f"\n✅ Finished. Total unique URLs: {len(all_urls)} (saved to {out_file})")

if __name__ == "__main__":
    scrape_women_clothing(last_page=1240, headless=False)

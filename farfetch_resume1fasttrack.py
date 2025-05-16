import os
import time
import csv
import random
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FFOptions
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def init_driver(headless=True, profile_dir=None):
    """
    Initialize a single Firefox webdriver instance for reuse across pages.
    """
    opts = FFOptions()
    if headless:
        opts.headless = True
    if profile_dir:
        opts.set_preference("profile", profile_dir)
    # Use a real UA string
    opts.set_preference(
        "general.useragent.override",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.110 Safari/537.36"
    )
    service = Service("/opt/homebrew/bin/geckodriver")
    driver = webdriver.Firefox(service=service, options=opts)
    driver.set_window_size(1920, 1080)
    # Lower implicit wait for speed; rely on explicit waits.
    driver.implicitly_wait(5)
    return driver


def close_signup_popup(driver, pause=0.5):
    try:
        btn = driver.find_element(
            By.XPATH,
            "//button[normalize-space(text())='×' or contains(@aria-label, 'Close')]"
        )
        btn.click()
        time.sleep(pause)
    except Exception:
        pass


def load_all_products(driver, pause=1, max_scrolls=5):
    """
    Scroll until no further height increase or max_scrolls reached.
    """
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def scrape_women_clothing(
    last_page: int = 1654,
    start_page: int = 1,
    headless: bool = True,
    profile_dir: str = None,
    max_retries: int = 2
):
    base_url = "https://www.farfetch.com/in/shopping/women/clothing-1/items.aspx"
    out_file = "women.csv"

    # Prepare CSV
    write_header = not os.path.exists(out_file) or start_page == 1
    mode = "w" if write_header else "a"
    csvfile = open(out_file, mode, newline="", encoding="utf-8")
    writer = csv.writer(csvfile)
    if write_header:
        writer.writerow(["product_url"])
        csvfile.flush()

    # Single driver for all pages
    driver = init_driver(headless=headless, profile_dir=profile_dir)
    # Suppress popup once
    driver.get("https://www.farfetch.com")
    driver.execute_script("window.localStorage.setItem('newsletter_popup_shown','true');")

    for page in range(start_page, last_page + 1):
        page_url = f"{base_url}?page={page}"
        print(f"\n→ Page {page}/{last_page}: {page_url}")

        attempt = 0
        success = False
        while attempt < max_retries and not success:
            try:
                driver.get(page_url)
                # wait up to 5s for product links
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR,
                        "a[href*='/shopping/'][href$='.aspx']"
                    ))
                )
                close_signup_popup(driver)
                load_all_products(driver)

                # Collect and write links immediately
                page_urls = {
                    a.get_attribute("href")
                    for a in driver.find_elements(
                        By.CSS_SELECTOR,
                        "a[href*='/shopping/'][href$='.aspx']"
                    )
                    if a.get_attribute("href") and "items.aspx" not in a.get_attribute("href")
                }
                for link in sorted(page_urls):
                    writer.writerow([link])
                csvfile.flush()

                print(f"  • Found and wrote {len(page_urls)} URLs")
                success = True

            except Exception as e:
                attempt += 1
                wait = 15 * attempt
                print(f"  !! Attempt {attempt}/{max_retries} failed ({e}). "
                      f"Backing off for {wait}s...")
                time.sleep(wait)

        if not success:
            print(f"  XX Skipping page {page} after {max_retries} attempts.")

        # short pause between pages
        time.sleep(random.uniform(1, 3))

    # Cleanup
    driver.quit()
    csvfile.close()
    print(f"\n✅ Done scraping {last_page - start_page + 1} pages. Data in {out_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--last-page", type=int, default=1654)
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--no-headless", action="store_true")
    args = parser.parse_args()

    scrape_women_clothing(
        last_page=args.last_page,
        start_page=args.start_page,
        headless=not args.no_headless
    )

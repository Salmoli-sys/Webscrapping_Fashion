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
import threading
import concurrent.futures


def init_driver(headless=True, profile_dir=None):
    """
    Initialize a Firefox webdriver instance.
    """
    opts = FFOptions()
    if headless:
        opts.headless = True
    if profile_dir:
        opts.set_preference("profile", profile_dir)
    # Use a real UA string
    opts.set_preference(
        "general.useragent.override",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.110 Safari/537.36"
    )
    service = Service("/opt/homebrew/bin/geckodriver")
    driver = webdriver.Firefox(service=service, options=opts)
    driver.set_window_size(1920, 1080)
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
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def process_batch(batch_pages, base_url, csvfile, writer, lock, headless, profile_dir):
    """
    Scrape a batch of pages using one driver instance, then quit.
    """
    driver = init_driver(headless=headless, profile_dir=profile_dir)
    # suppress popup once
    driver.get("https://www.farfetch.com")
    driver.execute_script("window.localStorage.setItem('newsletter_popup_shown','true');")

    for page in batch_pages:
        page_url = f"{base_url}?page={page}"
        print(f"→ Page {page}: {page_url}")
        attempt = 0
        success = False
        while attempt < 2 and not success:
            try:
                driver.get(page_url)
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR,
                        "a[href*='/shopping/'][href$='.aspx']"))
                )
                close_signup_popup(driver)
                load_all_products(driver)
                page_urls = {
                    a.get_attribute("href") for a in driver.find_elements(
                        By.CSS_SELECTOR, "a[href*='/shopping/'][href$='.aspx']"
                    ) if a.get_attribute("href") and "items.aspx" not in a.get_attribute("href")
                }
                with lock:
                    for link in sorted(page_urls):
                        writer.writerow([link])
                    csvfile.flush()
                print(f"  • Wrote {len(page_urls)} URLs from page {page}")
                success = True
            except Exception as e:
                attempt += 1
                wait = 15 * attempt
                print(f"  ! Retry {attempt} for page {page} after error: {e}")
                time.sleep(wait)
        time.sleep(random.uniform(1, 3))
    driver.quit()


def scrape_women_clothing(
    last_page: int = 1654,
    start_page: int = 1,
    headless: bool = True,
    profile_dir: str = None,
    workers: int = 4,
    batch_size: int = 10
):
    base_url = "https://www.farfetch.com/in/shopping/women/clothing-1/items.aspx"
    out_file = "women.csv"
    write_header = not os.path.exists(out_file) or start_page == 1
    mode = "w" if write_header else "a"

    csvfile = open(out_file, mode, newline="", encoding="utf-8")
    writer = csv.writer(csvfile)
    if write_header:
        writer.writerow(["product_url"])
        csvfile.flush()

    # Create page batches
    pages = list(range(start_page, last_page + 1))
    batches = [pages[i:i+batch_size] for i in range(0, len(pages), batch_size)]

    lock = threading.Lock()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        for batch in batches:
            futures.append(
                executor.submit(
                    process_batch,
                    batch,
                    base_url,
                    csvfile,
                    writer,
                    lock,
                    headless,
                    profile_dir
                )
            )
        # Optional: wait for all to complete
        for f in concurrent.futures.as_completed(futures):
            pass

    csvfile.close()
    print(f"\n✅ Done: scraped pages {start_page}–{last_page} with {workers} workers.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--last-page", type=int, default=1654)
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--no-headless", action="store_true")
    parser.add_argument("--workers", type=int, default=4,
                        help="Number of parallel workers (drivers)")
    parser.add_argument("--batch-size", type=int, default=10,
                        help="Pages per driver session before restart")
    args = parser.parse_args()

    scrape_women_clothing(
        last_page=args.last_page,
        start_page=args.start_page,
        headless=not args.no_headless,
        workers=args.workers,
        batch_size=args.batch_size
    )

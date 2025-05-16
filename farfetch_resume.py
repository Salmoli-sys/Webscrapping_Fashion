import os
import time
import csv
import argparse
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

def scrape_women_clothing(
    last_page: int = 1240,
    start_page: int = 1,
    headless: bool = True,
    profile_dir: str = None,
):
    # base_url = "https://www.farfetch.com/in/shopping/women/clothing-1/items.aspx"--1654
    base_url = "https://www.farfetch.com/in/shopping/men/clothing-2/items.aspx"
    out_file = "men.csv"
    all_urls = set()

    # 1) If CSV exists, load existing URLs so we don't re-append them
    if os.path.exists(out_file):
        with open(out_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if row:
                    all_urls.add(row[0])

    # 2) Decide write mode
    write_header = not os.path.exists(out_file) or start_page == 1
    mode = "w" if write_header else "a"

    with open(out_file, mode, newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if write_header:
            writer.writerow(["product_url"])
            csvfile.flush()

        # 3) Loop from start_page → last_page
        for page in range(start_page, last_page + 1):
            page_url = f"{base_url}?page={page}"
            print(f"\n→ Page {page}/{last_page}: {page_url}")

            driver = init_driver(headless=headless, profile_dir=profile_dir)
            # suppress newsletter popup
            driver.get("https://www.farfetch.com")
            driver.execute_script(
                "window.localStorage.setItem('newsletter_popup_shown','true');"
            )

            driver.get(page_url)
            time.sleep(2)
            close_signup_popup(driver)
            load_all_products(driver)

            # scrape this page
            page_urls = {
                itm.get_attribute("href")
                for itm in driver.find_elements(
                    By.CSS_SELECTOR, "a[href*='/shopping/'][href$='.aspx']"
                )
                if itm.get_attribute("href") and "items.aspx" not in itm.get_attribute("href")
            }
            driver.quit()

            # filter out ones we've already got
            new_urls = page_urls - all_urls
            all_urls.update(new_urls)

            # append just the new ones
            for link in sorted(new_urls):
                writer.writerow([link])
            csvfile.flush()

            print(f"  • Found {len(page_urls)} URLs, {len(new_urls)} new appended")

    print(f"\n✅ Done. Total unique URLs in {out_file}: {len(all_urls)}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--last-page", type=int, default=1240,
                   help="Final page number")
    p.add_argument("--start-page", type=int, default=1,
                   help="Page to start from (useful for resuming)")
    p.add_argument("--no-headless", action="store_true",
                   help="Run browser visibly")
    args = p.parse_args()

    scrape_women_clothing(
        last_page=args.last_page,
        start_page=args.start_page,
        headless=not args.no_headless
    )



# so i will run       python3 farfetch_resume.py --start-page 41 --no-headless

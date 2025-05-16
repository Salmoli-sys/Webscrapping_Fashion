
import os
import time
import csv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException


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
        close_btn = driver.find_element(
            By.XPATH,
            "//button[normalize-space(text())='×' or contains(@aria-label, 'Close')]"
        )
        close_btn.click()
        time.sleep(pause)
        print("  • Closed signup popup")
    except Exception:
        pass


def load_all_products(driver, pause=1):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(pause)


def scrape_farfetch_clothing(visuals=False, profile_dir=None):
    driver = init_driver(headless=not visuals, profile_dir=profile_dir)
    # Suppress signup modal
    driver.get("https://www.farfetch.com")
    driver.execute_script("window.localStorage.setItem('newsletter_popup_shown','true');")

    base_clothing_url = "https://www.farfetch.com/in/shopping/{section}/clothing-1/items.aspx"
    sections = ["women", "men", "kids"]

    for section in sections:
        print(f"\n→ Section: {section}")
        section_dir = os.path.join(section, 'clothing')
        os.makedirs(section_dir, exist_ok=True)

        # Only scrape the 'All clothing' page
        url = base_clothing_url.format(section=section)
        print(f"    – Scraping all clothing at: {url}")
        driver.get(url)
        time.sleep(2)
        close_signup_popup(driver)

        all_urls = set()
        page = 1
        while True:
            print(f"      · Page {page}")
            load_all_products(driver)
            items = driver.find_elements(
                By.CSS_SELECTOR, "a[href*='/shopping/'][href$='.aspx']"
            )
            for itm in items:
                href = itm.get_attribute('href')
                if href and 'items.aspx' not in href:
                    all_urls.add(href)

            # Click Next if available
            try:
                next_btn = driver.find_element(
                    By.CSS_SELECTOR,
                    "a[data-component='PaginationNextActionButton'][aria-disabled='false']"
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", next_btn)
                page += 1
                time.sleep(2)
                close_signup_popup(driver)
            except Exception:
                break

        # Write to CSV named 'all_clothing.csv'
        out_path = os.path.join(section_dir, 'all_clothing.csv')
        with open(out_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['product_url'])
            for u in sorted(all_urls):
                writer.writerow([u])
        print(f"      ▸ Saved {len(all_urls)} URLs to {out_path}")

    driver.quit()

if __name__ == '__main__':
    scrape_farfetch_clothing(visuals=True, profile_dir=None)


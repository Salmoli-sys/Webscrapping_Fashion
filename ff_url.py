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
        close_btn = driver.find_element(
            By.XPATH,
            "//button[normalize-space(text())='×' or contains(@aria-label, 'Close')]"
        )
        close_btn.click()
        time.sleep(pause)
        print("  • Closed signup popup")
    except Exception:
        pass


def load_all_products(driver, pause=2):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        try:
            btn = driver.find_element(By.XPATH, "//button[@data-test-id='infiniteScroll']")
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(pause)
        except Exception:
            pass
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def sanitize_slug(url):
    # Extracts the category slug from the URL and sanitizes it for filenames
    slug = url.rstrip('/').split('/')[-2]
    slug = ''.join(ch if ch.isalnum() else '_' for ch in slug.lower())
    return slug.strip('_')


def scrape_farfetch_clothing(visuals=False, profile_dir=None):
    driver = init_driver(headless=not visuals, profile_dir=profile_dir)

    # Suppress signup modal via localStorage
    driver.get("https://www.farfetch.com")
    driver.execute_script("window.localStorage.setItem('newsletter_popup_shown','true');")

    base_section_url = "https://www.farfetch.com/in/shopping/{section}/clothing-1/items.aspx"
    sections = ["women", "men", "kids"]

    for section in sections:
        print(f"\n→ Section: {section}")
        # Create section/clothing directory
        section_dir = os.path.join(section, 'clothing')
        os.makedirs(section_dir, exist_ok=True)

        # Navigate to the clothing listing page for this section
        driver.get(base_section_url.format(section=section))
        time.sleep(3)
        close_signup_popup(driver)

        # Find all subcategory links on the left sidebar
        subcat_els = driver.find_elements(
            By.XPATH,
            f"//a[contains(@href,'/in/shopping/{section}/') and contains(@href,'-1/items.aspx') and not(contains(@href,'clothing-1/items.aspx'))]"
        )
        subcats = []
        for a in subcat_els:
            href = a.get_attribute('href')
            if href and href not in subcats:
                subcats.append(href)
        print(f"  • Found {len(subcats)} sub-categories")

        # Scrape each subcategory and save its product URLs
        for url in subcats:
            print(f"    – Scraping: {url}")
            driver.get(url)
            time.sleep(3)
            close_signup_popup(driver)
            load_all_products(driver)

            items = driver.find_elements(
                By.CSS_SELECTOR,
                "a[href*='/shopping/'][href$='.aspx']"
            )
            seen_subcat = set()
            for itm in items:
                href = itm.get_attribute('href')
                if href and 'items.aspx' not in href:
                    seen_subcat.add(href)

            # Write subcategory CSV
            slug = sanitize_slug(url)
            out_path = os.path.join(section_dir, f"{slug}.csv")
            with open(out_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['product_url'])
                for u in sorted(seen_subcat):
                    writer.writerow([u])
            print(f"      ▸ Saved {len(seen_subcat)} URLs to {out_path}")

    driver.quit()


if __name__ == '__main__':
    scrape_farfetch_clothing(visuals=True, profile_dir=None)

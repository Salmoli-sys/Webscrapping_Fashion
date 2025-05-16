import os
import time
import csv
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

def init_driver(headless=True, profile_dir=None, geckodriver_path=None):
    opts = FirefoxOptions()
    if headless:
        opts.headless = True

    profile = FirefoxProfile(profile_dir) if profile_dir else None
    driver_args = {"options": opts}
    if profile:
        driver_args["firefox_profile"] = profile
    if geckodriver_path:
        driver_args["executable_path"] = geckodriver_path

    driver = webdriver.Firefox(**driver_args)
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

def sanitize_slug(url):
    slug = url.rstrip('/').split('/')[-2]
    return ''.join(ch if ch.isalnum() else '_' for ch in slug.lower()).strip('_')

def scrape_subcategory(section, url, visuals, profile_dir, geckodriver_path):
    """Worker: launch its own driver, scrape one sub-category, save URLs, then quit."""
    driver = init_driver(headless=not visuals,
                         profile_dir=profile_dir,
                         geckodriver_path=geckodriver_path)
    try:
        # suppress newsletter popup
        driver.get("https://www.farfetch.com")
        driver.execute_script("window.localStorage.setItem('newsletter_popup_shown','true');")
        time.sleep(1)

        driver.get(url)
        time.sleep(2)
        close_signup_popup(driver)

        all_urls = set()
        page = 1
        while True:
            load_all_products(driver)
            items = driver.find_elements(
                By.CSS_SELECTOR, "a[href*='/shopping/'][href$='.aspx']"
            )
            for itm in items:
                href = itm.get_attribute('href')
                if href and 'items.aspx' not in href:
                    all_urls.add(href)

            # try clicking “Next”
            try:
                pagination = driver.find_element(
                    By.CSS_SELECTOR, "div[data-component='PaginationWrapper']"
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", pagination)
                time.sleep(0.5)
                next_btn = driver.find_element(
                    By.CSS_SELECTOR,
                    "a[data-component='PaginationNextActionButton'][aria-disabled='false']"
                )
                driver.execute_script("arguments[0].click();", next_btn)
                page += 1
                time.sleep(2)
                close_signup_popup(driver)
            except NoSuchElementException:
                break
            except Exception:
                break

        # write out results
        section_dir = os.path.join(section, 'clothing')
        os.makedirs(section_dir, exist_ok=True)
        slug = sanitize_slug(url)
        out_path = os.path.join(section_dir, f"{slug}.csv")
        with open(out_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['product_url'])
            for u in sorted(all_urls):
                writer.writerow([u])
        print(f"✔ [{section}] {slug}: {len(all_urls)} URLs saved")
    finally:
        driver.quit()

def scrape_farfetch_clothing(visuals=False,
                            profile_dir=None,
                            geckodriver_path=None,
                            num_workers=4):
    # 1) gather all sub-category URLs sequentially
    base = "https://www.farfetch.com/in/shopping/{section}/clothing-1/items.aspx"
    sections = ["women", "men", "kids"]
    tasks = []

    # one driver is enough to collect sub-cats
    driver = init_driver(headless=True,
                         profile_dir=profile_dir,
                         geckodriver_path=geckodriver_path)
    driver.get("https://www.farfetch.com")
    driver.execute_script("window.localStorage.setItem('newsletter_popup_shown','true');")
    time.sleep(1)

    for section in sections:
        driver.get(base.format(section=section))
        time.sleep(2)
        close_signup_popup(driver)

        els = driver.find_elements(
            By.XPATH,
            f"//a[contains(@href, '/in/shopping/{section}/') "
            "and contains(@href, '-1/items.aspx') "
            "and not(contains(@href, 'clothing-1/items.aspx'))]"
        )
        seen = set()
        for a in els:
            href = a.get_attribute('href')
            if href and href not in seen:
                seen.add(href)
                tasks.append((section, href))

    driver.quit()
    print(f"→ Collected {len(tasks)} sub-categories; launching pool of {num_workers} workers…")

    # 2) dispatch workers
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as exe:
        futures = [
            exe.submit(scrape_subcategory, section, url, visuals, profile_dir, geckodriver_path)
            for section, url in tasks
        ]
        # optional: wait for all to finish
        concurrent.futures.wait(futures)

if __name__ == '__main__':
    scrape_farfetch_clothing(
        visuals=True,
        profile_dir=None,
        geckodriver_path=None,
        num_workers=4
    )

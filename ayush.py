import os
import time
import csv
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

def init_driver(headless=True, profile_dir=None, geckodriver_path=None):
    opts = FirefoxOptions()
    if headless:
        opts.headless = True

    profile = None
    if profile_dir:
        profile = FirefoxProfile(profile_dir)

    driver_args = {
        "options": opts
    }
    if profile:
        driver_args["firefox_profile"] = profile
    if geckodriver_path:
        driver_args["executable_path"] = geckodriver_path  # only if geckodriver not in PATH

    driver = webdriver.Firefox(**driver_args)
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

def sanitize_slug(url):
    slug = url.rstrip('/').split('/')[-2]
    return ''.join(ch if ch.isalnum() else '_' for ch in slug.lower()).strip('_')

def scrape_farfetch_clothing(visuals=False, profile_dir=None, geckodriver_path=None):
    driver = init_driver(headless=not visuals,
                         profile_dir=profile_dir,
                         geckodriver_path=geckodriver_path)

    driver.get("https://www.farfetch.com")
    # suppress the newsletter popup via localStorage
    driver.execute_script("window.localStorage.setItem('newsletter_popup_shown','true');")

    base_section = "https://www.farfetch.com/in/shopping/{section}/clothing-1/items.aspx"
    sections = ["women", "men", "kids"]

    for section in sections:
        print(f"\n→ Section: {section}")
        section_dir = os.path.join(section, 'clothing')
        os.makedirs(section_dir, exist_ok=True)

        driver.get(base_section.format(section=section))
        time.sleep(2)
        close_signup_popup(driver)

        # find all subcategory links under Clothing
        subcat_els = driver.find_elements(
            By.XPATH,
            f"//a[contains(@href, '/in/shopping/{section}/') and "
            "contains(@href, '-1/items.aspx') and "
            "not(contains(@href, 'clothing-1/items.aspx'))]"
        )
        subcats = []
        for a in subcat_els:
            href = a.get_attribute('href')
            if href and href not in subcats:
                subcats.append(href)
        print(f"  • Found {len(subcats)} sub-categories")

        for url in subcats:
            print(f"    – Scraping: {url}")
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

                # try to click the “Next” button in pagination
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

            slug = sanitize_slug(url)
            out_path = os.path.join(section_dir, f"{slug}.csv")
            with open(out_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['product_url'])
                for u in sorted(all_urls):
                    writer.writerow([u])
            print(f"      ▸ Saved {len(all_urls)} URLs to {out_path}")

    driver.quit()

if __name__ == '__main__':
    # visuals=True opens a visible Firefox window; you can pass geckodriver_path if needed
    scrape_farfetch_clothing(visuals=True, profile_dir=None, geckodriver_path=None)


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


def sanitize_slug(url):
    slug = url.rstrip('/').split('/')[-2]
    return ''.join(ch if ch.isalnum() else '_' for ch in slug.lower()).strip('_')


def scrape_farfetch_clothing(visuals=False, profile_dir=None):
    driver = init_driver(headless=not visuals, profile_dir=profile_dir)
    # Suppress signup modal
    driver.get("https://www.farfetch.com")
    driver.execute_script("window.localStorage.setItem('newsletter_popup_shown','true');")

    # --- Kids: first, scrape All clothing under each age group and gender ---
    print("\n→ Section: kids")
    driver.get("https://www.farfetch.com/in/shopping/kids/items.aspx")
    time.sleep(2)
    close_signup_popup(driver)

    age_groups = ["Baby (0-36mth)", "Kids (2-12 yrs)", "Teens (13-16 yrs)"]
    for age in age_groups:
        print(f"  • Age group: {age}")
        age_link = driver.find_element(
            By.CSS_SELECTOR, f"a[data-component='NavBarItemLink'][data-nav='{age}']"
        )
        panel_id = age_link.get_attribute('aria-controls')
        age_link.click()
        time.sleep(2)
        close_signup_popup(driver)
        panel = driver.find_element(By.ID, panel_id)

        sections = panel.find_elements(By.CSS_SELECTOR, "div[data-component='MegaNavNavigationSection']")
        for sec in sections:
            title_text = sec.find_element(
                By.CSS_SELECTOR, "p[data-component='MegaNavListTitle']"
            ).text.strip().lower().replace(' ', '_')
            try:
                all_elem = sec.find_element(By.LINK_TEXT, 'All clothing')
            except Exception:
                continue
            href = all_elem.get_attribute('href')
            print(f"    – Scraping {title_text} at: {href}")

            out_dir = os.path.join('kids', title_text)
            os.makedirs(out_dir, exist_ok=True)

            driver.get(href)
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
                    href2 = itm.get_attribute('href')
                    if href2 and 'items.aspx' not in href2:
                        all_urls.add(href2)
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

            out_path = os.path.join(out_dir, 'all_clothing.csv')
            with open(out_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['product_url'])
                for u in sorted(all_urls):
                    writer.writerow([u])
            print(f"      ▸ Saved {len(all_urls)} URLs to {out_path}")

    # --- Then Women & Men: scrape All clothing directly ---
    base_clothing_url = "https://www.farfetch.com/in/shopping/{section}/clothing-1/items.aspx"
    for section in ["women", "men"]:
        print(f"\n→ Section: {section}")
        section_dir = os.path.join(section, 'clothing')
        os.makedirs(section_dir, exist_ok=True)

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
                href2 = itm.get_attribute('href')
                if href2 and 'items.aspx' not in href2:
                    all_urls.add(href2)
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


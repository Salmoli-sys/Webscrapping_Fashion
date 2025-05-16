import os, csv, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from selenium.common.exceptions import StaleElementReferenceException

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# ─── CONFIG ────────────────────────────────────────────────────────────────────
KIDS_URL   = "https://www.farfetch.com/in/shopping/kids/items.aspx"
OUTPUT_DIR = "kidswear"

# section → map of folder-key to list of exact sub-category display names
CATEGORY_MAP = {
    "Baby (0-36mth)": {
        "Baby_Girls": [
            "Baby suits","Coats","Dresses","Jackets","Shorts",
            "Skirts","Swimwear","Tops","Tracksuits","Trousers"
        ],
        "Baby_Boys": [
            "Baby suits","Coats","Jackets","Shorts",
            "Swimwear","Tops","Tracksuits","Trousers"
        ],
    },
    "Kids (2-12 yrs)": {
        "Girls": [
            "Coats","Dresses","Denim","Jackets","Playsuits & jumpsuits",
            "Shorts","Skirts","Swimwear","Tops","Trousers"
        ],
        "Boys": [
            "Coats","Denim",
            "Jackets","Shorts","Swimwear","Tops","Tracksuits","Trousers"
        ],
    },
    "Teens (13-16 yrs)": {
        "Teen_girls": [
            "Coats","Denim","Dresses","Jackets",
            "Skirts","Swimwear","Tops","Trousers"
        ],
        "Teen_Boys": [
            "Coats","Denim","Jackets","Shorts",
            "Swimwear","Tops","Tracksuits","Trousers"
        ],
    },
}

def init_driver():
    opts = Options()
    # opts.add_argument("--headless")      # uncomment to hide browser
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    drv = webdriver.Chrome(options=opts)
    drv.set_window_size(1920, 1080)
    drv.implicitly_wait(5)
    return drv

def sanitize(s):
    return s.strip().replace(" ", "_").replace("&","and").replace("(", "").replace(")", "")





from urllib.parse import urljoin

def load_all_products(driver):
    """
    1) Grab all products on the current page
    2) If there’s a Next button (data-component="PaginationNextActionButton")
       that isn’t aria-disabled, extract its href, urljoin, driver.get(...)
    3) Loop until Next is disabled/missing
    4) Return the full list of URLs
    """
    pause = 1.5
    all_urls = []
    current_url = driver.current_url

    while True:
        time.sleep(pause)

        # collect this page’s product-card links
        cards = driver.find_elements(By.CSS_SELECTOR, "a[data-component='ProductCardLink']")
        for c in cards:
            href = c.get_attribute("href")
            if href:
                all_urls.append(href)

        # try to find the “Next” anchor
        try:
            nxt = driver.find_element(
                By.CSS_SELECTOR, "a[data-component='PaginationNextActionButton']"
            )
        except:
            break

        # stop if disabled
        if nxt.get_attribute("aria-disabled") == "true":
            break

        # get its href and navigate
        href = nxt.get_attribute("href")
        if not href:
            break
        next_url = href if href.startswith("http") else urljoin(current_url, href)

        driver.get(next_url)
        current_url = next_url

    return all_urls







def scrape_kids():
    driver = init_driver()
    wait   = WebDriverWait(driver, 10)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1) start on Kids landing
    driver.get(KIDS_URL)
    time.sleep(1)

    for section, groups in CATEGORY_MAP.items():
        for map_group_key, desired_subs in groups.items():
            group_display = map_group_key.replace("_", " ")  # e.g. "Baby Girls"
            section_dir   = os.path.join(OUTPUT_DIR, sanitize(section))
            group_dir     = os.path.join(section_dir, map_group_key)
            os.makedirs(group_dir, exist_ok=True)

            # 2) click the section tab to open fly-out
            tab = driver.find_element(By.XPATH, f"//a[@data-nav='{section}']")
            tab.click()

            # 3) wait for the mega-nav pop-over (it has id="meganav")
            meganav = wait.until(EC.visibility_of_element_located((By.ID, "meganav")))

            # 4) find the exact <p> header matching our group_display
            header = None
            for p in meganav.find_elements(By.TAG_NAME, "p"):
                if p.text.strip().lower() == group_display.lower():
                    header = p
                    break
            if not header:
                print("⚠️ couldn't find header", group_display)
                continue

            # 5) its next <ul> contains all sub-category <a> links
            ul = header.find_element(By.XPATH, "./following-sibling::ul[1]")
            # collect only the ones in our desired_subs list
            found = []
            for a in ul.find_elements(By.TAG_NAME, "a"):
                txt = a.text.strip()
                if txt in desired_subs:
                    found.append((txt, a.get_attribute("href")))

            # 6) iterate each sub-category link
            for txt, url in found:
                print(f"Scraping → {section} / {group_display} → {txt}")
                driver.get(url)
                time.sleep(1)

                all_urls = load_all_products(driver)
                unique   = sorted(set(all_urls))

                # 7) write CSV per sub-category
                out_csv = os.path.join(group_dir, f"{sanitize(txt)}.csv")
                with open(out_csv, "w", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(["product_url"])
                    for u in unique:
                        w.writerow([u])
                print(f"  • saved {len(unique)} URLs to {out_csv}")

    driver.quit()

if __name__ == "__main__":
    scrape_kids()

import os, csv, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin
import traceback

# ─── CONFIG ───────────────────────────────────────────────────────────────────
# Use the women clothing landing (clothing-1) URL
WOMEN_URL   = "https://www.farfetch.com/in/shopping/women/clothing-1/items.aspx"
OUTPUT_DIR  = "womenwear"

# Mapping must match data-nav exactly (lowercase) and the mega-nav header text
CATEGORY_MAP = {
    "women": {
        "Clothing": [
            "Activewear","Beachwear","Coats","Denim","Dresses",
            "Jackets","Knitwear","Lingerie","Skirts","Skiwear",
            "Tops","Trousers"
        ]
    }
}

# Initialize WebDriver
def init_driver():
    opts = Options()
    # opts.add_argument("--headless")  # uncomment to run headless
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=opts)
    driver.set_window_size(1920, 1080)
    driver.implicitly_wait(5)
    return driver

# Simple sanitizer for filenames
def sanitize(text):
    return text.strip().replace(" ", "_").replace("&", "and").replace("(", "").replace(")", "")

# Paginate through all product pages for current sub-category
def load_all_products(driver):
    pause = 1.5
    urls = []
    current_url = driver.current_url
    while True:
        time.sleep(pause)
        # collect product links on this page
        cards = driver.find_elements(By.CSS_SELECTOR, "a[data-component='ProductCardLink']")
        for c in cards:
            href = c.get_attribute("href")
            if href:
                urls.append(href)
        # try next button
        try:
            nxt = driver.find_element(By.CSS_SELECTOR, "a[data-component='PaginationNextActionButton']")
            if nxt.get_attribute("aria-disabled") == "true":
                break
            href = nxt.get_attribute("href")
            next_url = href if href.startswith("http") else urljoin(current_url, href)
            driver.get(next_url)
            current_url = next_url
        except Exception:
            break
    return urls

# Main scraping logic
def scrape_women():
    driver = init_driver()
    wait = WebDriverWait(driver, 10)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        # Open the women clothing landing page
        driver.get(WOMEN_URL)
        time.sleep(2)

        for section, groups in CATEGORY_MAP.items():
            for group_name, subs in groups.items():
                print(f"Processing nav '{section}' → '{group_name}'")
                group_dir = os.path.join(OUTPUT_DIR, sanitize(group_name))
                os.makedirs(group_dir, exist_ok=True)

                # click the Women nav to open the mega-menu
                tab = driver.find_element(By.XPATH, f"//a[@data-nav='{section}']")
                tab.click()
                meganav = wait.until(EC.visibility_of_element_located((By.ID, "meganav")))

                # find the header matching our group_name
                header = None
                for p in meganav.find_elements(By.TAG_NAME, "p"):
                    if p.text.strip().lower() == group_name.lower():
                        header = p
                        break
                if not header:
                    print(f"⚠️ Could not locate mega-nav header '{group_name}'")
                    continue

                # collect only desired sub-category links
                ul = header.find_element(By.XPATH, "./following-sibling::ul[1]")
                links = [(a.text.strip(), a.get_attribute('href')) for a in ul.find_elements(By.TAG_NAME, 'a') if a.text.strip() in subs]

                # scrape each sub-category
                for txt, url in links:
                    try:
                        print(f"Scraping → {txt}")
                        driver.get(url)
                        time.sleep(2)

                        all_urls = load_all_products(driver)
                        unique = sorted(set(all_urls))

                        out_csv = os.path.join(group_dir, f"{sanitize(txt)}.csv")
                        with open(out_csv, 'w', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerow(['product_url'])
                            for u in unique:
                                writer.writerow([u])
                        print(f"  • Saved {len(unique)} URLs to {out_csv}")
                    except Exception:
                        print(f"‼️ Error scraping '{txt}':")
                        traceback.print_exc()

    except Exception:
        print("‼️ Fatal error during setup:")
        traceback.print_exc()
    finally:
        # give a moment before closing
        time.sleep(3)
        driver.quit()
        print("Done. Browser closed.")

if __name__ == '__main__':
    scrape_women()

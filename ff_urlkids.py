import os, csv, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
            "Accessories","Shoes","Coats","Denim",
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

def load_all_products(driver):
    """Scroll + click “Load more” until exhausted, then return product URLs."""
    pause = 1.5
    last_h = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        new_h = driver.execute_script("return document.body.scrollHeight")
        if new_h == last_h:
            # try “Load more”
            try:
                btn = driver.find_element(By.XPATH, "//button[contains(., 'Load more')]")
                btn.click()
                time.sleep(pause)
                last_h = new_h
                continue
            except:
                break
        last_h = new_h

    cards = driver.find_elements(By.CSS_SELECTOR, "a[data-component='ProductCardLink']")
    return [c.get_attribute("href") for c in cards]

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

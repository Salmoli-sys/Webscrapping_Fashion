#script with the modal-killer logic injected immediately before each tab.click() so any stray pop-up is removed:
import os, csv, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from urllib.parse import urljoin

# ─── CONFIG ────────────────────────────────────────────────────────────────────
KIDS_URL   = "https://www.farfetch.com/in/shopping/kids/items.aspx"
OUTPUT_DIR = "kidswear"

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
    # opts.add_argument("--headless")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    drv = webdriver.Chrome(options=opts)
    drv.set_window_size(1920, 1080)
    drv.implicitly_wait(5)
    return drv

def sanitize(s):
    return s.strip().replace(" ", "_").replace("&","and").replace("(", "").replace(")", "")

def clear_modals(driver):
    """Remove any modal overlays or click their close buttons."""
    driver.execute_script("""
      document
        .querySelectorAll('div[data-component="ModalWrapper"]')
        .forEach(el => el.remove());
      document
        .querySelectorAll('button[data-component="ModalCloseButton"], button[aria-label="Close"], button[aria-label="Dismiss"]')
        .forEach(btn => btn.click());
    """)
    time.sleep(0.3)

def load_all_products(driver):
    """
    Paginate by following Next links until disabled.
    """
    pause = 1.5
    all_urls = []
    current_url = driver.current_url

    while True:
        time.sleep(pause)
        # collect this page’s product links
        cards = driver.find_elements(By.CSS_SELECTOR, "a[data-component='ProductCardLink']")
        for c in cards:
            href = c.get_attribute("href")
            if href:
                all_urls.append(href)

        # locate Next button
        try:
            nxt = driver.find_element(
                By.CSS_SELECTOR, "a[data-component='PaginationNextActionButton']"
            )
        except:
            break

        if nxt.get_attribute("aria-disabled") == "true":
            break

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

    driver.get(KIDS_URL)
    time.sleep(1)

    for section, groups in CATEGORY_MAP.items():
        for map_group_key, desired_subs in groups.items():
            group_display = map_group_key.replace("_", " ")
            section_dir   = os.path.join(OUTPUT_DIR, sanitize(section))
            group_dir     = os.path.join(section_dir, map_group_key)
            os.makedirs(group_dir, exist_ok=True)

            # remove any modal, then click section tab
            clear_modals(driver)
            tab = driver.find_element(By.XPATH, f"//a[@data-nav='{section}']")
            tab.click()

            # wait for fly-out
            meganav = wait.until(EC.visibility_of_element_located((By.ID, "meganav")))

            # find group header
            header = None
            for p in meganav.find_elements(By.TAG_NAME, "p"):
                if p.text.strip().lower() == group_display.lower():
                    header = p
                    break
            if not header:
                print("⚠️ couldn't find header", group_display)
                continue

            ul = header.find_element(By.XPATH, "./following-sibling::ul[1]")
            found = [(a.text.strip(), a.get_attribute("href"))
                     for a in ul.find_elements(By.TAG_NAME, "a")
                     if a.text.strip() in desired_subs]

            for txt, url in found:
                print(f"Scraping → {section} / {group_display} → {txt}")
                driver.get(url)
                time.sleep(1)

                all_urls = load_all_products(driver)
                unique   = sorted(set(all_urls))

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

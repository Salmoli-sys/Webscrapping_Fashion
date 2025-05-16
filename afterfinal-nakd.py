import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BASE_URL           = "https://www.na-kd.com"
CATEGORY_URL       = f"{BASE_URL}/en/category/jeans"

INITIAL_LOAD_PAUSE = 2    # seconds to wait after initial page load
CLICK_PAUSE        = 3    # wait after clicking “Load more” once
SCROLL_PAUSE       = 3    # wait after each subsequent scroll
MAX_NO_PROGRESS    = 15   # bounce after this many scrolls with no new items
MAX_TOTAL_ITERS    = 300  # safety cap on total scroll iterations

def get_fully_rendered_html(visual=False):
    opts = Options()
    if not visual:
        opts.add_argument("--headless")
    opts.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=opts)

    driver.get(CATEGORY_URL)
    time.sleep(INITIAL_LOAD_PAUSE)

    # initial “Load more” click
    try:
        btn = driver.find_element(By.XPATH, "//button[@data-test-id='infiniteScroll']")
        driver.execute_script("arguments[0].scrollIntoView(true);", btn)
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(CLICK_PAUSE)
    except:
        pass

    last_loaded     = 0
    no_progress_cnt = 0
    iters           = 0

    while iters < MAX_TOTAL_ITERS:
        iters += 1

        # if we’ve stalled, bounce (or retry “Load more”) before any further scroll-downs
        if no_progress_cnt >= MAX_NO_PROGRESS:
            print(" ⚠️ no progress—trying reload or bounce…")
            try:
                btn = driver.find_element(By.XPATH, "//button[@data-test-id='infiniteScroll']")
                driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(CLICK_PAUSE)
            except:
                # small up/down bounce
                driver.execute_script("window.scrollBy(0, -window.innerHeight * 0.5);")
                time.sleep(1)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(SCROLL_PAUSE)
            no_progress_cnt = 0
            continue

        # incremental scroll down in smaller steps
        for _ in range(10):
            driver.execute_script("window.scrollBy(0, window.innerHeight * 0.8);")
            time.sleep(SCROLL_PAUSE / 5)

        # check how many have loaded
        try:
            txt = driver.find_element(
                By.XPATH,
                "//div[contains(text(),' of ') and contains(text(),'products')]"
            ).text
            loaded, total = map(int, re.match(r"(\d+)\s+of\s+(\d+)", txt).groups())
            print(f" → loaded {loaded}/{total}")
            if loaded >= total:
                break

            if loaded > last_loaded:
                last_loaded     = loaded
                no_progress_cnt = 0
            else:
                no_progress_cnt += 1
        except:
            no_progress_cnt += 1

    html = driver.page_source
    driver.quit()
    return html

def extract_product_links(html):
    soup = BeautifulSoup(html, "html.parser")
    paths = {
        a["href"].split("?")[0]
        for a in soup.select("a[href^='/en/products/']")
    }
    return [BASE_URL + p for p in sorted(paths)]

def scrape_product_urls(visual=False):
    print("🔄 Loading page and clicking “Load more” once…")
    html = get_fully_rendered_html(visual)

    print("🔗 Extracting product URLs…")
    product_urls = extract_product_links(html)
    print(f"→ Found {len(product_urls)} products.")

    df = pd.DataFrame(product_urls, columns=["Product URL"])
    df.to_csv("na_kd_product_urls.csv", index=False)
    return df

if __name__ == "__main__":
    df = scrape_product_urls(visual=True)
    print(f"✅ Done! {len(df)} URLs → na_kd_product_urls.csv")

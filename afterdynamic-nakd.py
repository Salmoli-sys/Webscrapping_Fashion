import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BASE_URL             = "https://www.na-kd.com"
ROOT_CATEGORY_PATH   = "/en/products"        # your Clothing root
ROOT_CATEGORY_URL    = f"{BASE_URL}{ROOT_CATEGORY_PATH}"

INITIAL_LOAD_PAUSE = 2
CLICK_PAUSE        = 3
SCROLL_PAUSE       = 3
MAX_NO_PROGRESS    = 15
MAX_TOTAL_ITERS    = 300
FALLBACK_TIMEOUT   = 60

def get_fully_rendered_html(url, visual=False):
    start_time      = time.time()
    opts            = Options()
    if not visual:
        opts.add_argument("--headless")
        opts.add_argument("--disable-gpu")
    driver          = webdriver.Chrome(options=opts)

    driver.get(url)
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

        # ─── YOUR ORIGINAL BOUNCE / RETRY LOGIC ───────────────────────────
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

        # ─── YOUR NEW 60s‐TIMEOUT FALLBACK for subcategories jeans/baggy-jeans────────────────────────────────
        elapsed = time.time() - start_time
        if (
            elapsed > FALLBACK_TIMEOUT and
            no_progress_cnt >= MAX_NO_PROGRESS and
            not driver.find_elements(By.XPATH, "//button[@data-test-id='infiniteScroll']")
        ):
            print(f"⏱️  {FALLBACK_TIMEOUT}s elapsed with no progress and no “load more” → breaking early")
            break

    html = driver.page_source

    # if visual:
    #     print("\n🔎 Browser is still open. Press Enter here to close it…")
    #     input()

    driver.quit()
    return html

def extract_subcategory_urls(html):
    soup = BeautifulSoup(html, "html.parser")
    anchors = soup.select("div.sg-sub-categories-listing ul li a")
    return [urljoin(BASE_URL, a["href"]) for a in anchors if a.get("href")]

def extract_product_links(html):
    soup = BeautifulSoup(html, "html.parser")
    paths = { a["href"].split("?")[0] for a in soup.select("a[href^='/en/products/']") }
    return [BASE_URL + p for p in sorted(paths)]

def scrape_category(category_url, visual=False):
    print(f"\n🔄 Scraping category: {category_url}")
    html = get_fully_rendered_html(category_url, visual)
    print("🔗 Extracting product URLs…")
    product_urls = extract_product_links(html)
    print(f"→ Found {len(product_urls)} products.")
    slug = category_url.rstrip("/").split("/")[-1]
    fname = f"{slug}_product_urls.csv"
    pd.DataFrame(product_urls, columns=["Product URL"]).to_csv(fname, index=False)
    print(f"✅ Saved → {fname}")

if __name__ == "__main__":
    print(f"Loading root category page: {ROOT_CATEGORY_URL}")
    root_html = get_fully_rendered_html(ROOT_CATEGORY_URL, visual=True)
    subcats   = extract_subcategory_urls(root_html)
    print(f"Found {len(subcats)} sub-categories:")
    for url in subcats:
        print(" •", url)

    for cat_url in subcats:
        try:
            scrape_category(cat_url, visual=True)
        except Exception as e:
            print(f"❌ Error on {cat_url}: {e}")

    print("\n🎉 All done!")

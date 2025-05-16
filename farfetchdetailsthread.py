import csv
import time
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ─── CONFIG ────────────────────────────────────────────────────────────────────
INPUT_URLS_CSV  = "product_urls.csv"
OUTPUT_CSV      = "farfetch_products.csv"
WORKERS         = 3           # number of parallel Chrome windows
PAGE_LOAD_PAUSE = 3
POPUP_PAUSE     = 1
DETAILS_TIMEOUT = 5

def init_driver(headless=False):
    opts = Options()
    # omit --headless so you see each browser
    if headless:
        opts.add_argument("--headless")
        opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(10)
    return driver

def close_signup_popup(driver):
    try:
        btn = driver.find_element(
            By.XPATH,
            "//button[normalize-space(text())='×' or contains(@aria-label,'Close')]"
        )
        btn.click()
        time.sleep(POPUP_PAUSE)
    except NoSuchElementException:
        pass

def extract_with_new_driver(url):
    """
    Spins up its own Chrome instance, scrapes a single URL,
    and returns a dict with url/title/description/images.
    """
    driver = init_driver(headless=False)
    data = {"url": url, "title": "", "description": "", "images": []}

    try:
        driver.get(url)
        time.sleep(PAGE_LOAD_PAUSE)
        close_signup_popup(driver)

        # 1) Title
        try:
            h1 = driver.find_element(
                By.CSS_SELECTOR,
                "h1[data-component='ProductName'], h1"
            )
            data["title"] = h1.text.strip()
        except (NoSuchElementException, TimeoutException):
            pass

        # 2) “The Details” accordion
        try:
            sec = driver.find_element(
                By.XPATH,
                "//section[@data-component='AccordionItem'][.//p[normalize-space(.)='The Details']]"
            )
            btn = sec.find_element(By.CSS_SELECTOR, "button[data-component='AccordionButton']")
            panel = sec.find_element(By.CSS_SELECTOR, "div[data-component='AccordionPanel']")

            # only open if not already visible
            if not panel.is_displayed():
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});",
                    btn
                )
                time.sleep(0.3)
                driver.execute_script("arguments[0].click();", btn)
                WebDriverWait(sec, DETAILS_TIMEOUT).until(EC.visibility_of(panel))

            lines = [ln.strip() for ln in panel.text.splitlines() if ln.strip()]
            data["description"] = "; ".join(lines)

        except (NoSuchElementException, TimeoutException):
            pass

        # 3) Images
        imgs = driver.find_elements(
            By.CSS_SELECTOR,
            "img[data-component='Img'], div[data-component='Container'] img"
        )
        seen = set()
        for img in imgs:
            src = img.get_attribute("src")
            if src and src not in seen:
                seen.add(src)
                data["images"].append(src)

    finally:
        # give you a moment to see the finished browser before it closes
        time.sleep(1)
        driver.quit()

    return data

def main():
    # 1) load URLs
    with open(INPUT_URLS_CSV, newline="", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    # 2) open CSV writer
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as out:
        writer = csv.writer(out)
        writer.writerow(["Product URL", "Title", "Description", "Image URLs"])

        # 3) launch pool and submit
        with concurrent.futures.ProcessPoolExecutor(max_workers=WORKERS) as pool:
            future_to_url = {
                pool.submit(extract_with_new_driver, url): url
                for url in urls
            }

            # 4) write each result as it completes
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    item = future.result()
                    writer.writerow([
                        item["url"],
                        item["title"],
                        item["description"],
                        ";".join(item["images"])
                    ])
                    out.flush()
                    print(f"✅ done {url}")
                except Exception as e:
                    print(f"❌ error on {url}: {e}")

    print("🏁 All done – see", OUTPUT_CSV)

if __name__ == "__main__":
    main()

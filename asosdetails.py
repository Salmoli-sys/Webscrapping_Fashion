import csv
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

def init_driver(headless=False):
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    driver.implicitly_wait(10)
    return driver

def extract_product_info(driver, url):
    driver.get(url)
    time.sleep(2)

    # Title
    try:
        title = driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
    except NoSuchElementException:
        title = ""

    # Expand accordions
    for btn in driver.find_elements(By.CSS_SELECTOR, "button.accordion-item-module_titleBtn__"):
        if btn.get_attribute("aria-expanded") == "false":
            try:
                btn.click()
                time.sleep(0.2)
            except:
                pass

    # Description items
    desc_parts = []
    try:
        wrapper = driver.find_element(By.CSS_SELECTOR, "#productDescriptionDetails")
        for li in wrapper.find_elements(By.TAG_NAME, "li"):
            t = li.text.strip()
            if t:
                desc_parts.append(t)
    except NoSuchElementException:
        pass
    description = " | ".join(desc_parts)

    # Gallery images: pick highest-res from srcset
    image_urls = []
    for img in driver.find_elements(By.CSS_SELECTOR, "img.gallery-image"):
        srcset = img.get_attribute("srcset") or ""
        best = img.get_attribute("src")  # fallback
        max_w = 0
        for entry in srcset.split(","):
            parts = entry.strip().split(" ")
            if len(parts) == 2 and parts[1].endswith("w"):
                w = int(parts[1][:-1])
                if w > max_w:
                    max_w, best = w, parts[0]
        if best not in image_urls:
            image_urls.append(best)

    return title, description, image_urls

def main():
    driver = init_driver(headless=False)  # <-- visual=True
    with open("product_urls.csv", newline="", encoding="utf-8") as inf, \
         open("products.csv", "w", newline="", encoding="utf-8") as outf:

        reader = csv.reader(inf)
        header = next(reader, None)       # skip product_url header
        writer = csv.writer(outf)
        writer.writerow(["Product URL", "Title", "Description", "Image URLs"])

        for row in reader:
            url = row[0].strip()
            if not url:
                continue
            title, desc, imgs = extract_product_info(driver, url)
            writer.writerow([url, title, desc, "|".join(imgs)])
            print("✔", url)

    driver.quit()

if __name__ == "__main__":
    main()

import os
import base64
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ——— CONFIG ———
CSV_PATH   = "img.csv"  # ← replace with your CSV filename
URL_COL    = "image_urls"         # ← column that holds semicolon-separated URLs
OUTPUT_DIR = "downloaded_images"

# JS snippet to fetch an image URL and return a base64 string
JS_FETCH_BASE64 = """
const [url, callback] = arguments;
fetch(url)
  .then(res => {
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return res.blob();
  })
  .then(blob => new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result.split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  }))
  .then(b64 => callback(b64))
  .catch(() => callback(null));
"""

# ——— PREP OUTPUT DIR ———
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ——— SET UP SELENIUM ———
opts = Options()
opts.add_argument("--headless")
opts.add_argument("--disable-gpu")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    " AppleWebKit/537.36 (KHTML, like Gecko)"
    " Chrome/114.0.0.0 Safari/537.36"
)
driver = webdriver.Chrome(options=opts)
driver.set_window_size(1920, 1080)

# ——— READ CSV & PROCESS ROWS ———
df = pd.read_csv(CSV_PATH)

for row_idx, row in df.iterrows():
    folder_name = os.path.join(OUTPUT_DIR, f"row_{row_idx+1}")
    os.makedirs(folder_name, exist_ok=True)

    urls = str(row.get(URL_COL, "")).split(";")
    print(f"\n=== Row {row_idx+1}: {len(urls)} images → downloading into '{folder_name}'")

    for img_idx, raw_url in enumerate(urls, start=1):
        url = raw_url.strip()
        if not url:
            continue

        # use the full URL up to .jpg (including query params)
        direct_url = url

        # fetch via browser context
        driver.get("about:blank")
        b64 = driver.execute_async_script(JS_FETCH_BASE64, direct_url)
        if not b64:
            print(f" ⚠️  [{img_idx}] failed: {direct_url}")
            continue

        data = base64.b64decode(b64)
        out_file = os.path.join(folder_name, f"{img_idx}.jpg")
        with open(out_file, "wb") as f:
            f.write(data)
        print(f" ✅  [{img_idx}] saved")

driver.quit()
print("\nAll done!")

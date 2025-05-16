import os
import base64
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ——— CONFIG ———
CSV_FOLDER    = "csv_folder"   # ← folder containing all your .csv files
URL_COL       = "image_urls"                # ← name of the column with semicolon-separated URLs
OUTPUT_BASE   = "downloaded_images"         # ← root output folder

# JavaScript snippet to fetch an image as Base64 inside the browser
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

# ——— PREP OUTPUT ———
os.makedirs(OUTPUT_BASE, exist_ok=True)

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

# ——— PROCESS EACH CSV ———
for fname in os.listdir(CSV_FOLDER):
    if not fname.lower().endswith(".csv"):
        continue

    csv_path = os.path.join(CSV_FOLDER, fname)
    df = pd.read_csv(csv_path)

    # create folder for this CSV (without the .csv extension)
    base_name = os.path.splitext(fname)[0]
    output_csv_dir = os.path.join(OUTPUT_BASE, base_name)
    os.makedirs(output_csv_dir, exist_ok=True)

    print(f"\n▶ Processing '{fname}' → '{output_csv_dir}' ({len(df)} rows)")

    for row_idx, row in df.iterrows():
        row_folder = os.path.join(output_csv_dir, f"row_{row_idx+1}")
        os.makedirs(row_folder, exist_ok=True)

        urls = str(row.get(URL_COL, "")).split(";")
        print(f"  • Row {row_idx+1}: {len(urls)} images")

        for img_idx, raw_url in enumerate(urls, start=1):
            url = raw_url.strip()
            if not url:
                continue

            # fetch via Selenium/Fetch
            driver.get("about:blank")
            b64 = driver.execute_async_script(JS_FETCH_BASE64, url)
            if not b64:
                print(f"    ⚠️  [{img_idx}] failed: {url}")
                continue

            image_data = base64.b64decode(b64)
            out_path = os.path.join(row_folder, f"{img_idx}.jpg")
            with open(out_path, "wb") as f:
                f.write(image_data)

            print(f"    ✅  [{img_idx}] saved")

driver.quit()
print("\n✅ All done! Find your images under:", OUTPUT_BASE)

import os
import base64
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ——— CONFIG ———
CSV_FOLDER        = "csv_folder"        # folder containing all your .csv files
URL_COL           = "image_urls"                     # name of the column with semicolon-separated URLs
OUTPUT_IMG_ROOT   = "downloaded_images"      # root where images will be saved
OUTPUT_CSV_FOLDER = "output_csv_with_paths"  # where augmented CSVs go
NEW_COL           = "images_path"                    # column name for the image-paths

# make sure output folders exist
os.makedirs(OUTPUT_IMG_ROOT, exist_ok=True)
os.makedirs(OUTPUT_CSV_FOLDER, exist_ok=True)

# JavaScript snippet to fetch an image as Base64 inside the browser
JS_FETCH_BASE64 = """
const [url, callback] = arguments;
fetch(url)
  .then(res => { if (!res.ok) throw new Error('HTTP '+res.status); return res.blob(); })
  .then(blob => new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result.split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  }))
  .then(b64 => callback(b64))
  .catch(() => callback(null));
"""

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

    csv_path   = os.path.join(CSV_FOLDER, fname)
    df         = pd.read_csv(csv_path)
    base_name  = os.path.splitext(fname)[0]
    images_dir = os.path.join(OUTPUT_IMG_ROOT, base_name)
    os.makedirs(images_dir, exist_ok=True)

    print(f"\n▶ {fname}: {len(df)} rows → images → {images_dir}")

    images_path_list = []
    for row_idx, row in df.iterrows():
        row_folder = os.path.join(images_dir, f"row_{row_idx+1}")
        os.makedirs(row_folder, exist_ok=True)

        urls       = str(row.get(URL_COL, "")).split(";")
        saved_paths = []

        for img_idx, raw_url in enumerate(urls, start=1):
            url = raw_url.strip()
            if not url:
                continue

            # fetch image via browser fetch API
            driver.get("about:blank")
            b64 = driver.execute_async_script(JS_FETCH_BASE64, url)
            if not b64:
                print(f"   ⚠️  Row {row_idx+1} Img {img_idx} failed: {url}")
                continue

            img_data = base64.b64decode(b64)
            out_file = os.path.join(row_folder, f"{img_idx}.jpg")
            with open(out_file, "wb") as f:
                f.write(img_data)

            abs_path = os.path.abspath(out_file)
            saved_paths.append(abs_path)
            print(f"   ✅  Row {row_idx+1} Img {img_idx} saved")

        images_path_list.append(";".join(saved_paths))

    # add the new column and write augmented CSV
    df[NEW_COL] = images_path_list
    out_csv = os.path.join(OUTPUT_CSV_FOLDER, fname)
    df.to_csv(out_csv, index=False)
    print(f"✔ Wrote augmented CSV → {out_csv}")

driver.quit()
print("\n🎉 All done! Images under:", OUTPUT_IMG_ROOT, "  CSVs under:", OUTPUT_CSV_FOLDER)

import os
import base64
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ——— CONFIG ———
CSV_FOLDER        = "csv_folder"        # ← folder containing all your .csv files
URL_COL           = "image_urls"                     # ← name of the column with semicolon-separated URLs
OUTPUT_IMG_ROOT   = "downloaded_images"      # ← root where images will be saved
OUTPUT_CSV_FOLDER = "output_csv_with_paths"  # ← where augmented CSVs go
NEW_COL           = "images_path"                    # ← column name for the image-paths

# ensure output dirs exist
os.makedirs(OUTPUT_IMG_ROOT, exist_ok=True)
os.makedirs(OUTPUT_CSV_FOLDER, exist_ok=True)

# JavaScript snippet to fetch an image as Base64 in Chrome
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

    csv_path    = os.path.join(CSV_FOLDER, fname)
    base_name   = os.path.splitext(fname)[0]
    images_dir  = os.path.join(OUTPUT_IMG_ROOT, base_name)
    out_csv_path= os.path.join(OUTPUT_CSV_FOLDER, fname)

    # read original CSV
    df_orig = pd.read_csv(csv_path)

    # if an augmented CSV already exists, load it (so we can resume)
    if os.path.exists(out_csv_path):
        df = pd.read_csv(out_csv_path)
        print(f"↻ Resuming '{fname}', loaded {df[NEW_COL].notna().sum()} of {len(df)} rows done.")
    else:
        df = df_orig.copy()
        df[NEW_COL] = ""                  # initialize blank
        print(f"▶ Starting '{fname}' ({len(df)} rows)")

    os.makedirs(images_dir, exist_ok=True)

    # iterate rows
    for idx, row in df.iterrows():
        # skip if already done
        if isinstance(row[NEW_COL], str) and row[NEW_COL].strip():
            continue

        # prepare row folder
        row_folder = os.path.join(images_dir, f"row_{idx+1}")
        os.makedirs(row_folder, exist_ok=True)

        raw_urls = str(row.get(URL_COL, "")).split(";")
        saved = []

        for img_i, raw in enumerate(raw_urls, start=1):
            url = raw.strip()
            if not url:
                continue

            driver.get("about:blank")
            b64 = driver.execute_async_script(JS_FETCH_BASE64, url)
            if not b64:
                print(f"  ⚠️  {base_name} row {idx+1} img{img_i} failed")
                continue

            data = base64.b64decode(b64)
            out_file = os.path.join(row_folder, f"{img_i}.jpg")
            with open(out_file, "wb") as f:
                f.write(data)
            saved.append(os.path.abspath(out_file))
            print(f"  ✅ {base_name} row {idx+1} img{img_i}")

        # record and immediately flush to disk
        df.at[idx, NEW_COL] = ";".join(saved)
        df.to_csv(out_csv_path, index=False)

    print(f"✔ Finished '{fname}', wrote {out_csv_path}")

driver.quit()
print("\n🏁 All done! Images →", OUTPUT_IMG_ROOT, "  CSVs →", OUTPUT_CSV_FOLDER)

import os
import base64
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from multiprocessing import Pool, current_process

# ——— CONFIG ———
CSV_FOLDER        = "csv_folder"        # folder containing your .csv files
URL_COL           = "image_urls"                     # column with semicolon-separated URLs
OUTPUT_IMG_ROOT   = "downloaded_images"      # where images will be saved
OUTPUT_CSV_FOLDER = "output_csv_with_paths"  # where augmented CSVs go
NEW_COL           = "images_path"                    # new column for image-paths
N_WORKERS         = 4                                 # adjust to your CPU/RAM
RESTART_THRESHOLD = 50                                # restart Chrome every 50 rows

# ensure output dirs exist
os.makedirs(OUTPUT_IMG_ROOT, exist_ok=True)
os.makedirs(OUTPUT_CSV_FOLDER, exist_ok=True)

# JavaScript snippet for fetch→Base64
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

# Globals per worker
driver = None
process_count = 0

def init_worker():
    """Initializer for each pool worker: spin up its own headless Chrome."""
    global driver, process_count
    process_count = 0
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
    print(f"[{current_process().name}] ChromeDriver initialized")

def process_row(args):
    """
    Worker function: downloads all images for one row, returns (csv_name, row_idx, images_path_str).
    args = (csv_name, row_idx, raw_urls, OUTPUT_IMG_ROOT)
    """
    global driver, process_count

    csv_name, row_idx, raw_urls, output_img_root = args
    base_name = os.path.splitext(csv_name)[0]
    images_dir = os.path.join(output_img_root, base_name, f"row_{row_idx+1}")
    os.makedirs(images_dir, exist_ok=True)

    # Restart driver periodically
    process_count += 1
    if process_count % RESTART_THRESHOLD == 0:
        try:
            driver.quit()
        except:
            pass
        init_worker()
        print(f"[{current_process().name}] Restarted ChromeDriver after {process_count} rows")

    urls = str(raw_urls).split(";")
    saved = []
    for img_i, raw in enumerate(urls, start=1):
        url = raw.strip()
        if not url:
            continue

        try:
            driver.get("about:blank")
            b64 = driver.execute_async_script(JS_FETCH_BASE64, url)
        except Exception as e:
            print(f"[{current_process().name}] ⚠️ fetch exception row{row_idx+1} img{img_i}: {e}")
            continue

        if not b64:
            # empty response; will be retried later
            continue

        data = base64.b64decode(b64)
        out_file = os.path.join(images_dir, f"{img_i}.jpg")
        with open(out_file, "wb") as f:
            f.write(data)
        saved.append(os.path.abspath(out_file))

    return (csv_name, row_idx, ";".join(saved))

if __name__ == "__main__":
    pool = Pool(processes=N_WORKERS, initializer=init_worker)

    for fname in os.listdir(CSV_FOLDER):
        if not fname.lower().endswith(".csv"):
            continue

        csv_path     = os.path.join(CSV_FOLDER, fname)
        out_csv_path = os.path.join(OUTPUT_CSV_FOLDER, fname)
        print(f"\n▶ Processing '{fname}'")

        df_orig = pd.read_csv(csv_path)
        if os.path.exists(out_csv_path):
            df = pd.read_csv(out_csv_path)
            done = df[NEW_COL].str.strip().astype(bool).sum()
            print(f"  ↻ Resuming: {done}/{len(df)} rows done")
        else:
            df = df_orig.copy()
            df[NEW_COL] = ""
            print(f"  ▶ Starting fresh: {len(df)} rows")

        # **First pass**: dispatch all incomplete rows
        tasks = [
            (fname, idx, row.get(URL_COL, ""), OUTPUT_IMG_ROOT)
            for idx, row in df.iterrows()
            if not (isinstance(row[NEW_COL], str) and row[NEW_COL].strip())
        ]
        for csv_name, row_idx, img_paths in pool.imap_unordered(process_row, tasks):
            df.at[row_idx, NEW_COL] = img_paths
            df.to_csv(out_csv_path, index=False)

        # **Retry pass**: pick up any rows still empty
        remaining = [
            (fname, idx, row.get(URL_COL, ""), OUTPUT_IMG_ROOT)
            for idx, row in df.iterrows()
            if not row[NEW_COL].strip()
        ]
        if remaining:
            print(f"  🔁 Retrying {len(remaining)} failed rows...")
            for csv_name, row_idx, img_paths in pool.imap_unordered(process_row, remaining):
                df.at[row_idx, NEW_COL] = img_paths
                df.to_csv(out_csv_path, index=False)

        print(f"  ✔ Finished '{fname}', wrote '{out_csv_path}'")

    pool.close()
    pool.join()
    print("\n🏁 All done! Images →", OUTPUT_IMG_ROOT, " CSVs →", OUTPUT_CSV_FOLDER)

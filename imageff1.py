import os
import glob
import requests
import pandas as pd

# ——— CONFIG ———
CSV_DIR      = "csv_folder"    # ← folder containing all your .csv files
URL_COLUMN   = "Image URLs"                 # ← the column header with semicolon-separated URLs
OUTPUT_ROOT  = "downloaded_images"          # ← root folder for all downloads

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        " AppleWebKit/537.36 (KHTML, like Gecko)"
        " Chrome/114.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.farfetch.com/"
}

# ——— PREP OUTPUT ROOT ———
os.makedirs(OUTPUT_ROOT, exist_ok=True)

# ——— PROCESS EACH CSV ———
for csv_path in glob.glob(os.path.join(CSV_DIR, "*.csv")):
    csv_name = os.path.splitext(os.path.basename(csv_path))[0]
    csv_out_dir = os.path.join(OUTPUT_ROOT, csv_name)
    os.makedirs(csv_out_dir, exist_ok=True)
    print(f"\nProcessing `{csv_name}.csv` → folder: `{csv_out_dir}`")

    # read CSV
    df = pd.read_csv(csv_path)

    for idx, row in df.iterrows():
        row_num = idx + 1
        row_folder = os.path.join(csv_out_dir, f"row_{row_num}")
        os.makedirs(row_folder, exist_ok=True)

        raw = str(row.get(URL_COLUMN, "")).strip()
        if not raw:
            print(f"  • Row {row_num}: no URLs found.")
            continue

        urls = [u.strip() for u in raw.split(";") if u.strip()]
        print(f"  • Row {row_num}: {len(urls)} image(s) → `{row_folder}`")

        for img_idx, url in enumerate(urls, start=1):
            try:
                resp = requests.get(url, headers=HEADERS, timeout=15, stream=True)
                resp.raise_for_status()
                out_path = os.path.join(row_folder, f"{img_idx}.jpg")
                with open(out_path, "wb") as f:
                    for chunk in resp.iter_content(1024):
                        f.write(chunk)
                print(f"    ✅ [{img_idx}] saved")
            except Exception as e:
                print(f"    ⚠️ [{img_idx}] failed: {url} ({e})")

print("\nAll downloads complete!")

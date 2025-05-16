import os
import glob
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ——— CONFIG ———
CSV_DIR         = "csv_folder"            # ← folder containing your original .csv files
URL_COLUMN      = "Image URLs"            # ← column with semicolon-separated URLs
DOWNLOAD_ROOT   = "downloaded_images"     # ← where images get saved
OUTPUT_CSV_DIR  = "csv_with_image_paths"  # ← where the annotated CSVs go

# ensure output dirs exist
os.makedirs(DOWNLOAD_ROOT,  exist_ok=True)
os.makedirs(OUTPUT_CSV_DIR, exist_ok=True)

# ——— SESSION WITH RETRIES ———
session = requests.Session()
retry_strategy = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        " AppleWebKit/537.36 (KHTML, like Gecko)"
        " Chrome/114.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.farfetch.com/"
})

# ——— PROCESS EACH CSV ———
for csv_path in glob.glob(os.path.join(CSV_DIR, "*.csv")):
    csv_name    = os.path.splitext(os.path.basename(csv_path))[0]
    download_dir = os.path.join(DOWNLOAD_ROOT, csv_name)
    os.makedirs(download_dir, exist_ok=True)

    print(f"\n⏳ Processing `{csv_name}.csv`…")
    df = pd.read_csv(csv_path)

    # load or initialize images_path column
    out_csv = os.path.join(OUTPUT_CSV_DIR, f"{csv_name}.csv")
    if os.path.exists(out_csv):
        prev = pd.read_csv(out_csv)
        if "images_path" in prev.columns:
            df["images_path"] = prev["images_path"]
        else:
            df["images_path"] = ""
    else:
        df["images_path"] = ""

    # iterate rows
    for idx, row in df.iterrows():
        row_num = idx + 1
        already = str(row["images_path"]).strip()
        if already:
            print(f"  • Row {row_num}: already done, skipping.")
            continue

        row_folder = os.path.join(download_dir, f"row_{row_num}")
        os.makedirs(row_folder, exist_ok=True)

        raw = str(row.get(URL_COLUMN, "")).strip()
        if not raw:
            print(f"  • Row {row_num}: no URLs found.")
            df.at[idx, "images_path"] = ""
            df.to_csv(out_csv, index=False)
            continue

        urls = [u.strip() for u in raw.split(";") if u.strip()]
        print(f"  • Row {row_num}: downloading {len(urls)} image(s)…")

        saved = []
        for img_idx, url in enumerate(urls, start=1):
            fname = f"{img_idx}.jpg"
            out_path = os.path.join(row_folder, fname)

            # skip if file already exists
            if os.path.exists(out_path):
                saved.append(os.path.abspath(out_path))
                print(f"    ↪️ [{img_idx}] exists, skipping download")
                continue

            try:
                resp = session.get(url, timeout=15, stream=True)
                resp.raise_for_status()
                with open(out_path, "wb") as f:
                    for chunk in resp.iter_content(1024):
                        f.write(chunk)
                saved.append(os.path.abspath(out_path))
                print(f"    ✅ [{img_idx}] saved")
            except Exception as e:
                print(f"    ⚠️ [{img_idx}] failed: {e}")

        df.at[idx, "images_path"] = ";".join(saved)
        # checkpoint after each row
        df.to_csv(out_csv, index=False)

    print(f"✔ Finished `{csv_name}` → {out_csv}")

print("\n🎉 All done!")

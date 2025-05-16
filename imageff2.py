import os
import glob
import requests
import pandas as pd

# ——— CONFIG ———
CSV_DIR         = "csv_folder"            # ← folder containing your original .csv files
URL_COLUMN      = "Image URLs"            # ← the column header with semicolon-separated URLs
DOWNLOAD_ROOT   = "downloaded_images"     # ← where images get saved
OUTPUT_CSV_DIR  = "csv_with_image_paths"  # ← where the new CSVs will go

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        " AppleWebKit/537.36 (KHTML, like Gecko)"
        " Chrome/114.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.farfetch.com/"
}

# ensure output dirs exist
os.makedirs(DOWNLOAD_ROOT,   exist_ok=True)
os.makedirs(OUTPUT_CSV_DIR,  exist_ok=True)

# ——— PROCESS EACH CSV ———
for csv_path in glob.glob(os.path.join(CSV_DIR, "*.csv")):
    csv_name   = os.path.splitext(os.path.basename(csv_path))[0]
    download_dir = os.path.join(DOWNLOAD_ROOT, csv_name)
    os.makedirs(download_dir, exist_ok=True)

    print(f"\n⏳ Processing `{csv_name}.csv`…")
    df = pd.read_csv(csv_path)
    images_paths = []

    for idx, row in df.iterrows():
        row_num    = idx + 1
        row_folder = os.path.join(download_dir, f"row_{row_num}")
        os.makedirs(row_folder, exist_ok=True)

        raw = str(row.get(URL_COLUMN, "")).strip()
        if not raw:
            images_paths.append("")
            print(f"  • Row {row_num}: no URLs")
            continue

        urls = [u.strip() for u in raw.split(";") if u.strip()]
        print(f"  • Row {row_num}: {len(urls)} image(s)")

        saved_paths = []
        for img_idx, url in enumerate(urls, start=1):
            try:
                resp = requests.get(url, headers=HEADERS, timeout=15, stream=True)
                resp.raise_for_status()
                fname = f"{img_idx}.jpg"
                out_path = os.path.join(row_folder, fname)
                with open(out_path, "wb") as f:
                    for chunk in resp.iter_content(1024):
                        f.write(chunk)
                abs_path = os.path.abspath(out_path)
                saved_paths.append(abs_path)
                print(f"    ✅ [{img_idx}] saved")
            except Exception as e:
                print(f"    ⚠️ [{img_idx}] failed: {e}")

        images_paths.append(";".join(saved_paths))

    # append new column and write out augmented CSV
    df["images_path"] = images_paths
    out_csv = os.path.join(OUTPUT_CSV_DIR, f"{csv_name}.csv")
    df.to_csv(out_csv, index=False)
    print(f"✔ Wrote augmented CSV → {out_csv}")

print("\n🎉 All done!")

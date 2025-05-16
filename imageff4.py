import os
import glob
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed

# ——— CONFIG ———
CSV_DIR         = "csv_folder"             # folder containing your original CSVs
URL_COLUMN      = "Image URLs"             # column header with semicolon-separated URLs
DOWNLOAD_ROOT   = "downloaded_images"      # where images get saved
OUTPUT_CSV_DIR  = "csv_with_image_paths"   # where the annotated CSVs go
MAX_WORKERS     = 4                        # reduce or bump depending on your RAM/CPU
REINIT_EVERY    = 50                       # restart session every N rows

# create needed dirs
os.makedirs(DOWNLOAD_ROOT,  exist_ok=True)
os.makedirs(OUTPUT_CSV_DIR, exist_ok=True)

def create_session():
    """Return a requests.Session with retries configured."""
    s = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            " AppleWebKit/537.36 (KHTML, like Gecko)"
            " Chrome/114.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.farfetch.com/"
    })
    return s

def download_row(session, csv_name, row_num, raw_urls):
    """
    Download all images for one row.
    Returns: (row_num, semicolon‐joined absolute paths).
    """
    try:
        download_dir = os.path.join(DOWNLOAD_ROOT, csv_name, f"row_{row_num}")
        os.makedirs(download_dir, exist_ok=True)

        if not raw_urls.strip():
            return row_num, ""

        urls = [u.strip() for u in raw_urls.split(";") if u.strip()]
        saved = []
        for idx, url in enumerate(urls, start=1):
            fname = f"{idx}.jpg"
            out_path = os.path.join(download_dir, fname)

            # skip if already there
            if os.path.exists(out_path):
                saved.append(os.path.abspath(out_path))
                continue

            try:
                resp = session.get(url, timeout=15, stream=True)
                resp.raise_for_status()
                with open(out_path, "wb") as f:
                    for chunk in resp.iter_content(1024):
                        f.write(chunk)
                saved.append(os.path.abspath(out_path))
            except Exception as e:
                print(f"    ⚠️  Row {row_num} image {idx} failed: {e}")
        return row_num, ";".join(saved)

    except Exception as e:
        # catch anything unexpected per-row
        print(f"  ⚠️  Unexpected error on row {row_num}: {e}")
        return row_num, ""

# ——— MAIN LOOP ———
for csv_path in glob.glob(os.path.join(CSV_DIR, "*.csv")):
    csv_name = os.path.splitext(os.path.basename(csv_path))[0]
    print(f"\n🔄 Processing `{csv_name}.csv`…")

    # load original CSV
    df = pd.read_csv(csv_path)
    out_csv = os.path.join(OUTPUT_CSV_DIR, f"{csv_name}.csv")

    # if we have a previous run, pull in its images_path to skip done rows
    if os.path.exists(out_csv):
        prev = pd.read_csv(out_csv)
        df["images_path"] = prev.get("images_path", "")
    else:
        df["images_path"] = ""

    # build list of rows still to do
    to_do = [
        (csv_name, idx+1, str(df.at[idx, URL_COLUMN] or ""))
        for idx in df.index
        if not str(df.at[idx, "images_path"]).strip()
    ]

    # process in chunks of REINIT_EVERY
    for batch_start in range(0, len(to_do), REINIT_EVERY):
        batch = to_do[batch_start: batch_start + REINIT_EVERY]
        session = create_session()

        print(f"→ Rows {batch_start+1} to {batch_start+len(batch)}")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(download_row, session, name, rn, urls): (rn, urls)
                for name, rn, urls in batch
            }
            for future in as_completed(futures):
                rn, paths = future.result()
                df.at[rn-1, "images_path"] = paths
                status = "no URLs" if not paths else f"{len(paths.split(';'))} image(s)"
                print(f"  • Row {rn}: {status}")
                # checkpoint after each row
                df.to_csv(out_csv, index=False)

    print(f"✅ Finished `{csv_name}` → {out_csv}")

print("\n🎉 All done!")

import os
import glob
import re
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed

# ——— CONFIG ———
CSV_DIR         = "csv_folder"             # your folder of CSVs
TITLE_COLUMN    = "Title"                  # product title column
URL_COLUMN      = "Image URLs"             # semicolon-separated URLs
DOWNLOAD_ROOT   = "downloaded_images"      # where to save images
OUTPUT_CSV_DIR  = "csv_with_image_paths"   # where to write annotated CSVs
MAX_WORKERS     = 4                        # tune to your RAM/CPU
REINIT_EVERY    = 50                       # restart session every N rows

os.makedirs(DOWNLOAD_ROOT,  exist_ok=True)
os.makedirs(OUTPUT_CSV_DIR, exist_ok=True)

def create_session():
    s = requests.Session()
    retry = Retry(total=5, backoff_factor=1,
                  status_forcelist=[429,500,502,503,504],
                  allowed_methods=["GET"])
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

def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name)
    return cleaned.strip().replace(" ", "_")

def download_row(session, csv_name, row_num, title, raw_urls):
    """Download missing images for one row; return full images_path."""
    safe = sanitize_filename(title) or f"row{row_num}"
    folder_name = f"{safe}_row{row_num}"
    row_folder = os.path.join(DOWNLOAD_ROOT, csv_name, folder_name)
    os.makedirs(row_folder, exist_ok=True)

    urls = [u.strip() for u in raw_urls.split(";") if u.strip()]
    saved = []

    for idx, url in enumerate(urls, start=1):
        fname = f"{folder_name}_{idx}.jpg"
        out_path = os.path.join(row_folder, fname)

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
            print(f"    ✅ Row{row_num} img{idx} saved")
        except Exception as e:
            print(f"    ⚠️ Row{row_num} img{idx} failed: {e}")

    return row_num, saved

# ——— MAIN LOOP ———
for csv_path in glob.glob(os.path.join(CSV_DIR, "*.csv")):
    csv_name = os.path.splitext(os.path.basename(csv_path))[0]
    print(f"\n🔄 Processing `{csv_name}.csv`…")

    df = pd.read_csv(csv_path)
    out_csv = os.path.join(OUTPUT_CSV_DIR, f"{csv_name}.csv")
    df["images_path"] = ""  # we’ll rebuild it from disk

    # build list of rows needing work
    to_do = []
    for idx, row in df.iterrows():
        rn = idx + 1
        raw = str(row.get(URL_COLUMN, "") or "")
        urls = [u for u in raw.split(";") if u.strip()]
        safe = sanitize_filename(str(row.get(TITLE_COLUMN, ""))) or f"row{rn}"
        folder_name = f"{safe}_row{rn}"
        row_folder = os.path.join(DOWNLOAD_ROOT, csv_name, folder_name)

        # gather whatever's already on disk
        existing_files = []
        if os.path.isdir(row_folder):
            for fn in os.listdir(row_folder):
                path = os.path.join(row_folder, fn)
                if os.path.isfile(path):
                    existing_files.append(os.path.abspath(path))

        if len(existing_files) >= len(urls):
            # done or no URLs
            df.at[idx, "images_path"] = ";".join(sorted(existing_files))
            print(f"  • Row {rn}: already {len(existing_files)}/{len(urls)} images")
        else:
            # needs (re)download
            to_do.append((csv_name, rn, row.get(TITLE_COLUMN, ""), raw))

    # process in batches to re-init session
    for start in range(0, len(to_do), REINIT_EVERY):
        batch = to_do[start:start+REINIT_EVERY]
        session = create_session()
        print(f"→ Rows {start+1}–{start+len(batch)}…")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as exe:
            futures = {
                exe.submit(download_row, session, name, rn, title, urls): (rn, urls)
                for name, rn, title, urls in batch
            }
            for fut in as_completed(futures):
                rn, saved = fut.result()
                df.at[rn-1, "images_path"] = ";".join(sorted(saved))
                print(f"  • Row {rn}: now {len(saved)} image(s)")
                # checkpoint
                df.to_csv(out_csv, index=False)

    # final write (in case no batches ran)
    df.to_csv(out_csv, index=False)
    print(f"✅ Finished `{csv_name}` → {out_csv}")

print("\n🎉 All done!")

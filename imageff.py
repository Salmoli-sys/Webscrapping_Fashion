import os
import requests
import pandas as pd

CSV_PATH   = "img.csv"
URL_COL    = "image_urls"
OUTPUT_DIR = "downloaded_images"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                  " AppleWebKit/537.36 (KHTML, like Gecko)"
                  " Chrome/114.0.0.0 Safari/537.36",
    "Referer": "https://www.farfetch.com/"
}

os.makedirs(OUTPUT_DIR, exist_ok=True)
df = pd.read_csv(CSV_PATH)

for row_idx, row in df.iterrows():
    folder = os.path.join(OUTPUT_DIR, f"row_{row_idx+1}")
    os.makedirs(folder, exist_ok=True)
    urls = str(row.get(URL_COL, "")).split(";")
    print(f"\n=== Row {row_idx+1}: {len(urls)} images → '{folder}'")

    for img_idx, url in enumerate(urls, start=1):
        url = url.strip()
        if not url:
            continue
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10, stream=True)
            resp.raise_for_status()
            out_path = os.path.join(folder, f"{img_idx}.jpg")
            with open(out_path, "wb") as f:
                for chunk in resp.iter_content(1024):
                    f.write(chunk)
            print(f" ✅  [{img_idx}] saved")
        except Exception as e:
            print(f" ⚠️  [{img_idx}] failed: {url} ({e})")
print("\nAll done!")

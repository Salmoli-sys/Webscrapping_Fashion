import os
import pandas as pd

# ——— CONFIG ———
CSV_FOLDER     = "csv_folder"         # folder containing your original CSVs
DOWNLOAD_ROOT  = "downloaded_images"       # root where images were saved
OUTPUT_FOLDER  = "output_csv_with_paths"   # folder to write new CSVs

URL_COL        = "image_urls"      # name of the column in the original CSV
NEW_COL        = "images_path"     # name of the new column to add

# make sure the output folder exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# iterate over every CSV in the source folder
for fname in os.listdir(CSV_FOLDER):
    if not fname.lower().endswith(".csv"):
        continue

    csv_path = os.path.join(CSV_FOLDER, fname)
    df = pd.read_csv(csv_path)

    base_name = os.path.splitext(fname)[0]
    output_csv_dir = os.path.join(OUTPUT_FOLDER)
    # (we’re flat here – you’ll get output_csv_with_paths/men_activewear.csv, etc.)

    # build the list of image-path strings, one per row
    images_path_list = []
    for idx in range(len(df)):
        # the folder where row idx+1’s images live:
        row_dir = os.path.join(DOWNLOAD_ROOT, base_name, f"row_{idx+1}")
        if os.path.isdir(row_dir):
            # list all .jpg (or adjust if you use other extensions)
            files = sorted(f for f in os.listdir(row_dir) if f.lower().endswith(".jpg"))
            # make absolute paths (or leave relative if you prefer)
            full_paths = [os.path.abspath(os.path.join(row_dir, f)) for f in files]
            images_path_list.append(";".join(full_paths))
        else:
            images_path_list.append("")  # no folder → empty string

    # add the new column and write out
    df[NEW_COL] = images_path_list
    out_csv_path = os.path.join(OUTPUT_FOLDER, fname)
    df.to_csv(out_csv_path, index=False)
    print(f"✔ Wrote {out_csv_path}")

print("✅ All CSVs processed.")

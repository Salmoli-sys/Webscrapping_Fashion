import os
import base64
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ——— CONFIG ———
URLS = [
    # strip off their resizing query and add “.jpg”
    "https://images.asos-media.com/products/adidas-football-inter-miami-home-jersey-in-pink/207197378-1-pink?$n_1920w$&wid=1926&fit=constrain.jpg",
"https://images.asos-media.com/products/adidas-football-inter-miami-home-jersey-in-pink/207197378-4?$n_1920w$&wid=1926&fit=constrain.jpg"
]
OUTPUT_DIR = "downloaded_images"

# ——— PREP ———
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ——— SET UP SELENIUM ———
opts = Options()
opts.add_argument("--headless")
opts.add_argument("--disable-gpu")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
# optional: spoof UA
opts.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    " AppleWebKit/537.36 (KHTML, like Gecko)"
    " Chrome/114.0.0.0 Safari/537.36"
)
driver = webdriver.Chrome(options=opts)
driver.set_window_size(1920, 1080)

# ——— JS SNIPPET TO PULL IMAGE AS BASE64 ———
js_fetch_to_base64 = """
const [url, callback] = arguments;
fetch(url)
  .then(res => {
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return res.blob();
  })
  .then(blob => new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result.split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  }))
  .then(b64 => callback(b64))
  .catch(err => callback(null));
"""

for idx, img_url in enumerate(URLS, start=1):
    print(f"→ Fetching image #{idx}…")
    # load a blank page so fetch runs in page context
    driver.get("about:blank")
    b64 = driver.execute_async_script(js_fetch_to_base64, img_url)
    if not b64:
        print(f"⚠️  Failed to fetch #{idx}")
        continue

    data = base64.b64decode(b64)
    out_path = os.path.join(OUTPUT_DIR, f"jersey_{idx}.jpg")
    with open(out_path, "wb") as f:
        f.write(data)
    print(f"✅  Saved {out_path}")

driver.quit()
print("Done!")

import os
import re
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import pytesseract
from PIL import Image
import cv2
import numpy as np

from pymongo import MongoClient, ASCENDING
from pymongo.errors import PyMongoError


BASE_DIR = Path(__file__).parent
IMG_DIR = BASE_DIR / "card_images"
OUT_DIR = BASE_DIR / "output"
OUT_DIR.mkdir(exist_ok=True)

# ----------------------------
# MongoDB setup
# ----------------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "amazon_ocr")
MONGO_COL = os.getenv("MONGO_COL", "gpu_laptops")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
col = db[MONGO_COL]

# Create a helpful unique index to prevent duplicates:
# If you have ASIN, use that. If not, fallback to image_file.
# We'll keep both and upsert by whichever is present.
col.create_index([("asin", ASCENDING)], unique=False)
col.create_index([("image_file", ASCENDING)], unique=True)

# ----------------------------
# Tesseract setup (your paths)
# ----------------------------
TESS_EXE = r"C:\Users\harshs\Ctrix\.venv\Lib\site-packages\tesseract.exe"
TESSDATA_DIR = r"C:\Users\harshs\Ctrix\.venv\Lib\site-packages\tessdata"

if not Path(TESS_EXE).exists():
    raise FileNotFoundError(f"tesseract.exe not found: {TESS_EXE}")
if not Path(TESSDATA_DIR, "eng.traineddata").exists():
    raise FileNotFoundError(f"eng.traineddata not found: {Path(TESSDATA_DIR, 'eng.traineddata')}")

pytesseract.pytesseract.tesseract_cmd = TESS_EXE
os.environ["TESSDATA_PREFIX"] = TESSDATA_DIR
OCR_CONFIG = f"--oem 3 --psm 6 --tessdata-dir {TESSDATA_DIR}"

# ----------------------------
# GPU filters
# ----------------------------
GPU_INCLUDE = [
    r"\brtx\b", r"\bgtx\b", r"\bgeforce\b", r"\bnvidia\b",
    r"\bradeon\b", r"\brx\b", r"\bamd\s+radeon\b",
]
GPU_EXCLUDE = [
    r"\bintel\b", r"\buhd\b", r"\biris\b", r"\bintegrated\b",
    r"\buma\b", r"\bshared\b", r"\barc\b"
]

def has_nvidia_amd_gpu(text: str) -> bool:
    t = (text or "").lower()
    include_hit = any(re.search(p, t) for p in GPU_INCLUDE)
    exclude_hit = any(re.search(p, t) for p in GPU_EXCLUDE)
    return include_hit and not exclude_hit

def preprocess(pil_img: Image.Image):
    arr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return th

PRICE_RE = re.compile(r"(₹\s?\d[\d,]*|\b\d{1,3}(?:,\d{3})+\b)")
RATING_RE = re.compile(r"(\d(?:\.\d)?)\s*out\s*of\s*5", re.IGNORECASE)

def extract_fields(text: str):
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]

    title = ""
    for ln in lines[:15]:
        if PRICE_RE.search(ln):
            continue
        if RATING_RE.search(ln):
            continue
        if len(ln) > len(title) and len(ln) >= 10:
            title = ln

    price = ""
    m = PRICE_RE.search(text or "")
    if m:
        price = m.group(1).replace(" ", "")

    rating = ""
    m = RATING_RE.search(text or "")
    if m:
        rating = m.group(1)

    return title, price, rating

# ----------------------------
# Helpers: parse metadata from filename
# Example: card_p01_03_B0XXXXXXX.png
# ----------------------------
FNAME_RE = re.compile(r"card_p(?P<page>\d+)_?(?P<idx>\d+)_?(?P<asin>[A-Z0-9]{8,15})", re.IGNORECASE)

def parse_meta_from_filename(fname: str):
    m = FNAME_RE.search(fname)
    if not m:
        return {}
    d = m.groupdict()
    return {
        "page": int(d["page"]) if d.get("page") else None,
        "index": int(d["idx"]) if d.get("idx") else None,
        "asin": (d.get("asin") or "").upper()
    }

# ----------------------------
# Mongo upsert function
# ----------------------------
def upsert_to_mongo(doc: dict):
    """
    Upserts by ASIN if available; otherwise upserts by image_file.
    """
    try:
        if doc.get("asin"):
            key = {"asin": doc["asin"]}
        else:
            key = {"image_file": doc["image_file"]}

        # setOnInsert keeps initial create timestamp stable
        now = datetime.now(timezone.utc)
        update = {
            "$set": {**doc, "updated_at": now},
            "$setOnInsert": {"created_at": now}
        }

        col.update_one(key, update, upsert=True)

    except PyMongoError as e:
        print(f" MongoDB error while writing {doc.get('image_file')}: {e}")

def main():
    if not IMG_DIR.exists():
        raise FileNotFoundError(f"card_images folder not found: {IMG_DIR}")

    images = sorted(IMG_DIR.glob("*.png"))
    print("\n🔍 Starting OCR on card_images...\n")
    print("Images found:", len(images))

    results_for_csv = []

    for img_path in images:
        print(f"Processing {img_path.name} ...")

        try:
            pil = Image.open(img_path)
        except Exception as e:
            print(f" Could not open {img_path.name}: {e}\n")
            continue

        pre = preprocess(pil)
        text = pytesseract.image_to_string(pre, config=OCR_CONFIG, lang="eng")

        if not has_nvidia_amd_gpu(text):
            print("   -> skip (no NVIDIA/AMD GPU keywords)\n")
            continue

        title, price, rating = extract_fields(text)
        if not title:
            print("   -> skip (title not found)\n")
            continue

        meta = parse_meta_from_filename(img_path.name)

        doc = {
            "image_file": img_path.name,
            "image_path": str(img_path),
            "title": title,
            "price": price,
            "rating": rating,
            "raw_text": text,           # useful for debugging
            "source": "amazon_in_cards", # tag your pipeline
            **meta
        }

        # ✅ write to MongoDB immediately
        upsert_to_mongo(doc)

        print(f" ✅ saved to MongoDB: {title[:70]} | {price} | {rating}\n")

        # optional: still collect for CSV
        results_for_csv.append({
            "image_file": img_path.name,
            "title": title,
            "price": price,
            "rating": rating
        })

    # optional CSV export
    df = pd.DataFrame(results_for_csv)
    out_csv = OUT_DIR / "gpu_laptops_from_images.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")

    print(" DONE. Saved:", out_csv)
    print("Total NVIDIA/AMD GPU laptops found:", len(df))

if __name__ == "__main__":
    main()
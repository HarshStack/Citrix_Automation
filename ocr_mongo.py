# ocr_mongo.py
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
import pytesseract

from pymongo import MongoClient, ASCENDING
from pymongo.errors import PyMongoError

# ----------------------------
# MongoDB config
# ----------------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "amazon_ocr")
MONGO_COL = os.getenv("MONGO_COL", "gpu_laptops")

_client = MongoClient(MONGO_URI)
_db = _client[MONGO_DB]
_col = _db[MONGO_COL]

# Useful indexes
_col.create_index([("asin", ASCENDING)], unique=False)
_col.create_index([("image_file", ASCENDING)], unique=True)

# ----------------------------
# Tesseract config
# ----------------------------
TESS_EXE = os.getenv("TESS_EXE", r"C:\Users\harshs\Ctrix\.venv\Lib\site-packages\tesseract.exe")
TESSDATA_DIR = os.getenv("TESSDATA_DIR", r"C:\Users\harshs\Ctrix\.venv\Lib\site-packages\tessdata")

if not Path(TESS_EXE).exists():
    raise FileNotFoundError(f"tesseract.exe not found: {TESS_EXE}")
if not Path(TESSDATA_DIR, "eng.traineddata").exists():
    raise FileNotFoundError(f"eng.traineddata not found: {Path(TESSDATA_DIR, 'eng.traineddata')}")

pytesseract.pytesseract.tesseract_cmd = TESS_EXE
os.environ["TESSDATA_PREFIX"] = TESSDATA_DIR
OCR_CONFIG = f"--oem 3 --psm 6 --tessdata-dir {TESSDATA_DIR}"


# ----------------------------
# Filters + extractors
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
# Streaming function: OCR + Mongo Upsert
# ----------------------------
def ocr_and_store(image_path: str, asin: str, page: int, index: int, query: str = "") -> dict | None:
    """
    Returns inserted/updated doc (as dict-like), or None if skipped.
    """
    img_path = Path(image_path)
    if not img_path.exists():
        return None

    pil = Image.open(img_path)
    pre = preprocess(pil)
    text = pytesseract.image_to_string(pre, config=OCR_CONFIG, lang="eng")

    # GPU filter
    if not has_nvidia_amd_gpu(text):
        return None

    title, price, rating = extract_fields(text)
    if not title:
        return None

    now = datetime.now(timezone.utc)

    doc = {
        "asin": (asin or "").upper(),
        "query": query,
        "page": page,
        "index": index,
        "image_file": img_path.name,
        "image_path": str(img_path),
        "title": title,
        "price": price,
        "rating": rating,
        "raw_text": text,
        "source": "amazon_in_cards",
        "updated_at": now,
    }

    try:
        # Prefer ASIN as key if present, else fall back to image_file
        key = {"asin": doc["asin"]} if doc["asin"] else {"image_file": doc["image_file"]}

        _col.update_one(
            key,
            {"$set": doc, "$setOnInsert": {"created_at": now}},
            upsert=True
        )
        return doc

    except PyMongoError as e:
        print(f"[MongoDB] Error storing {img_path.name}: {e}")
        return None
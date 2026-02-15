# ocr_ext.py
import os
import re
from pathlib import Path

import cv2
import numpy as np
import pytesseract
from PIL import Image

# ---------
# Regex (tolerant for OCR quirks)
# ---------
PRICE_RE = re.compile(r"(₹\s?\d[\d,]*|\b\d{1,3}(?:,\d{3})+\b)")
RATING_RE = re.compile(r"(\d(?:\.\d)?)\s*out\s*of\s*5", re.IGNORECASE)
REVIEWS_RE = re.compile(r"(\d[\d,]*)\s*(ratings|rating|reviews|review)", re.IGNORECASE)

def configure_tesseract():
    """
    Configure pytesseract and return (tess_exe, tessdata_dir, ocr_config).
    Uses env vars if present; otherwise uses your venv paths.
    """
    tess_exe = os.getenv(
        "TESSERACT_EXE",
        r"C:\Users\harshs\Ctrix\.venv\Lib\site-packages\tesseract.exe"
    )
    tessdata_dir = os.getenv(
        "TESSDATA_DIR",
        r"C:\Users\harshs\Ctrix\.venv\Lib\site-packages\tessdata"
    )

    if not Path(tess_exe).exists():
        raise FileNotFoundError(f"Tesseract EXE not found: {tess_exe}")
    if not Path(tessdata_dir).exists():
        raise FileNotFoundError(f"Tessdata directory not found: {tessdata_dir}")

    pytesseract.pytesseract.tesseract_cmd = tess_exe
    ocr_config = rf'--oem 3 --psm 6 --tessdata-dir "{tessdata_dir}"'
    return tess_exe, tessdata_dir, ocr_config

def preprocess_for_ocr(pil_img: Image.Image):
    """
    Improve OCR accuracy: grayscale -> upscale -> denoise -> threshold
    """
    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return th

def extract_fields(text: str) -> dict:
    """
    Extract title/model, price, rating, reviews from OCR text.
    """
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]

    # Title/model heuristic: longest meaningful line among first ~10 lines
    title = ""
    for ln in lines[:10]:
        if "₹" in ln:
            continue
        if len(ln) > len(title) and len(ln) >= 12:
            title = ln

    price = ""
    m = PRICE_RE.search(text or "")
    if m:
        price = m.group(1).replace(" ", "")

    rating = ""
    m = RATING_RE.search(text or "")
    if m:
        rating = m.group(1)

    reviews = ""
    m = REVIEWS_RE.search(text or "")
    if m:
        reviews = m.group(1)

    return {"title_model": title, "price": price, "rating": rating, "reviews": reviews}

def ocr_extract_from_card(image_path: Path, ocr_config: str, dump_text_dir: Path | None = None) -> dict:
    """
    OCR a card screenshot and return extracted fields + raw OCR text.
    """
    pil = Image.open(image_path)
    pre = preprocess_for_ocr(pil)

    text = pytesseract.image_to_string(pre, config=ocr_config, lang="eng")

    if dump_text_dir:
        dump_text_dir.mkdir(parents=True, exist_ok=True)
        (dump_text_dir / f"{image_path.stem}.txt").write_text(text, encoding="utf-8")

    fields = extract_fields(text)
    fields["ocr_text"] = text
    return fields
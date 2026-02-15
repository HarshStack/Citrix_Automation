# pipeline.py
from pathlib import Path
import pandas as pd

from ocr_ext import configure_tesseract, ocr_extract_from_card
from filter_gpu import has_nvidia_amd_discrete_gpu
from collector import collect_card_screenshots

# =========================
# PIPELINE CONFIG
# =========================
QUERY = "gaming laptop"
TARGET_COUNT = 10

MAX_PAGES = 8          # increase if you don't get 10 GPU laptops quickly
CARDS_PER_PAGE = 12    # capture a bit more than 10 because filter removes many

BASE_DIR = Path(__file__).parent
OUT_DIR = BASE_DIR / "output"
OUT_DIR.mkdir(exist_ok=True)

DUMP_OCR_TEXT = True   # saves OCR text per card for debugging


def main():
    # Setup OCR
    tess_exe, tessdata_dir, ocr_config = configure_tesseract()
    print("✅ Tesseract EXE:", tess_exe)
    print("✅ Tessdata:", tessdata_dir)

    # Collect card screenshots
    collected = collect_card_screenshots(
        query=QUERY,
        max_pages=MAX_PAGES,
        cards_per_page=CARDS_PER_PAGE,
        base_dir=BASE_DIR,
        headless=False,
    )

    if not collected:
        print("No screenshots collected. Possibly blocked or selectors changed.")
        return

    # OCR + Filter GPU
    results = []
    dump_dir = (OUT_DIR / "ocr_text") if DUMP_OCR_TEXT else None

    for item in collected:
        img_path = Path(item["image_path"])

        fields = ocr_extract_from_card(img_path, ocr_config, dump_text_dir=dump_dir)

        combined_text = (fields.get("title_model", "") + " " + fields.get("ocr_text", ""))
        if not has_nvidia_amd_discrete_gpu(combined_text):
            continue

        row = {
            "page": item["page"],
            "index": item["index"],
            "asin": item["asin"],
            "image_file": img_path.name,
            "title_model": fields.get("title_model", ""),
            "price": fields.get("price", ""),
            "rating": fields.get("rating", ""),
            "reviews": fields.get("reviews", ""),
        }
        results.append(row)

        print(f"[GPU ✅] {len(results)}/{TARGET_COUNT} -> {row['title_model'][:70]} | {row['price']} | {row['rating']}")

        if len(results) >= TARGET_COUNT:
            break

    # Export
    df = pd.DataFrame(results)
    out_csv = OUT_DIR / "amazon_in_gpu_top10_ocr.csv"
    out_xlsx = OUT_DIR / "amazon_in_gpu_top10_ocr.xlsx"

    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="GPU_Top10")

    print("\n✅ Saved:", out_csv)
    print("✅ Saved:", out_xlsx)
    print("Total GPU laptops extracted:", len(df))


if __name__ == "__main__":
    main()
from pathlib import Path
import pandas as pd
from ocr_ext import configure_tesseract, ocr_extract_from_card
from filter_gpu import has_nvidia_amd_discrete_gpu

BASE_DIR = Path(__file__).parent
IMG_DIR = BASE_DIR / "card_images"
OUT_DIR = BASE_DIR / "output"
OUT_DIR.mkdir(exist_ok=True)

TARGET_COUNT = 10

def main():
    _, _, ocr_config = configure_tesseract()
    dump_dir = OUT_DIR / "ocr_text"
    results = []

    for img_path in sorted(IMG_DIR.glob("*.png")):
        fields = ocr_extract_from_card(img_path, ocr_config, dump_text_dir=dump_dir)
        combined = fields.get("title_model","") + " " + fields.get("ocr_text","")

        if not has_nvidia_amd_discrete_gpu(combined):
            continue

        results.append({
            "image_file": img_path.name,
            "title_model": fields.get("title_model",""),
            "price": fields.get("price",""),
            "rating": fields.get("rating",""),
            "reviews": fields.get("reviews",""),
        })

        print(f"[GPU ✅] {len(results)}/{TARGET_COUNT} -> {results[-1]['title_model'][:70]}")

        if len(results) >= TARGET_COUNT:
            break

    df = pd.DataFrame(results)
    df.to_csv(OUT_DIR / "gpu_top10_from_existing_images.csv", index=False, encoding="utf-8-sig")
    print("Saved:", OUT_DIR / "gpu_top10_from_existing_images.csv")

if __name__ == "__main__":
    main()
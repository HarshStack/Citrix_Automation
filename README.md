# Citrix_Automation

Features

Collector (Selenium): opens Amazon.in search page (e.g., gaming laptop), paginates via DOM “Next”, and saves element-level screenshots for each result card to card_images/.
OCR 
(Tesseract): preprocesses card images (grayscale, upscale, denoise, threshold) and reads text with Tesseract.
Field extraction: pulls Title, Price (₹), and Rating from OCR text via regex heuristics.
GPU filter (NVIDIA/AMD only): keeps results mentioning RTX/GTX/GeForce/NVIDIA/Radeon/RX and excludes Intel/Iris/UHD/Integrated/UMA/Arc.
Exports: saves CSV and Excel with a Summary sheet.

🗂️ Project Structure
Ctrix/
  collector.py          # Selenium: open amazon.in, paginate, save card screenshots
  ocr_from_images.py    # OCR: read card_images, extract fields, GPU-filter, save CSV/XLSX
  ocr_ext.py            # (optional module form) OCR helpers used by pipeline
  filter_gpu.py         # (optional module) GPU include/exclude logic
  pipeline.py           # (optional) Orchestrates collector → OCR → export
  card_images/          # Output from collector (PNG screenshots per card)
  output/               # CSV/XLSX, debug artifacts
  templates/            # (optional) if using image templates for RPA experiments
  README.md

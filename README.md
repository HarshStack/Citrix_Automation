# Citrix_Automation

Features

-Collector (Selenium): opens Amazon.in search page (e.g., gaming laptop), paginates via DOM “Next”, and saves element-level screenshots for each result card to card_images/.
-OCR (Tesseract): preprocesses card images (grayscale, upscale, denoise, threshold) and reads text with Tesseract.
-Field extraction: pulls Title, Price (₹), and Rating from OCR text via regex heuristics.
-GPU filter (NVIDIA/AMD only): keeps results mentioning RTX/GTX/GeForce/NVIDIA/Radeon/RX and excludes Intel/Iris/UHD/Integrated/UMA/Arc.
-Exports: saves CSV and Excel with a Summary sheet.

🗂️ Project Structure

Ctrix/

  collector.py                   # Selenium: open amazon.in, paginate, save card screenshots
  
  ocr_from_images.py             # OCR: read card_images, extract fields, GPU-filter, save CSV/XLSX
  
  ocr_ext.py                     # (optional module form) OCR helpers used by pipeline
  
  filter_gpu.py                  # (optional module) GPU include/exclude logic
  
  pipeline.py                    # (optional) Orchestrates collector → OCR → export
  
  card_images/                   # Output from collector (PNG screenshots per card)
  
  output/                        # CSV/XLSX, debug artifacts


Requirements

Python 3.11+

Chrome (latest) + ChromeDriver compatible with your Chrome

Tesseract OCR engine (Windows):

tesseract.exe

tessdata/eng.traineddata

Python packages:


🧠 How It Works
Hybrid Architecture

[ Selenium ] --open amazon.in--> [ Search Results ]
      |                                  |
      |--element.screenshot() per card-->+--> [ card_images/*.png ]
                                          
[ OCR Pipeline ] --Tesseract on card PNGs--> [ text ]
                --> regex extract fields (title/price/rating)
                --> GPU keywords filter (NVIDIA/AMD only)
                --> save CSV + Excel

OCR Preprocessing

Convert to grayscale
Upscale ×2 (helps OCR)
Bilateral filter (denoise, preserve edges)
Otsu threshold

Field Extraction Heuristics

Title: longest non-price, non-rating line among first ~15 lines
Price: ₹ or comma-separated number (regex)
Rating: x out of 5 (regex)

GPU Filter
Include: RTX, GTX, GeForce, NVIDIA, Radeon, RX, AMD Radeon
Exclude: Intel, UHD, Iris, Integrated, UMA, Shared, Arc


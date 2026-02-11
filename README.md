# Citrix_Automation
Features

Collector (Selenium): opens Amazon.in search page (e.g., gaming laptop), paginates via DOM “Next”, and saves element-level screenshots for each result card to card_images/.
OCR (Tesseract): preprocesses card images (grayscale, upscale, denoise, threshold) and reads text with Tesseract.
Field extraction: pulls Title, Price (₹), and Rating from OCR text via regex heuristics.
GPU filter (NVIDIA/AMD only): keeps results mentioning RTX/GTX/GeForce/NVIDIA/Radeon/RX and excludes Intel/Iris/UHD/Integrated/UMA/Arc.
Exports: saves CSV and Excel with a Summary sheet.

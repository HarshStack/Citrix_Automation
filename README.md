# Citrix_Automation

Features

-Collector (Selenium): opens Amazon.in search page (e.g., gaming laptop), paginates via DOM “Next”, and saves element-level screenshots for each result card to card_images/.
-OCR (Tesseract): preprocesses card images (grayscale, upscale, denoise, threshold) and reads text with Tesseract.
-Field extraction: pulls Title, Price (₹), and Rating from OCR text via regex heuristics.
-GPU filter (NVIDIA/AMD only): keeps results mentioning RTX/GTX/GeForce/NVIDIA/Radeon/RX and excludes Intel/Iris/UHD/Integrated/UMA/Arc.
-Exports: saves CSV and Excel with a Summary sheet.

🗂️ Project Structure

<img width="1092" height="410" alt="image" src="https://github.com/user-attachments/assets/0186ba46-75f6-4994-be1d-ba601c08928c" />


Requirements


Python 3.11+

Chrome (latest) + ChromeDriver compatible with your Chrome

Tesseract OCR engine (Windows):

tesseract.exe

tessdata/eng.traineddata

Python packages:


🧠 How It Works

Hybrid Architecture

<img width="881" height="348" alt="image" src="https://github.com/user-attachments/assets/071929fc-6bc8-40d5-88a9-8ff406d527b2" />


OCR Preprocessing:

Convert to grayscale,
Upscale ×2 (helps OCR),
Bilateral filter (denoise, preserve edges),
Otsu threshold

Field Extraction Heuristics:

Title: longest non-price, non-rating line among first ~15 lines,
Price: ₹ or comma-separated number (regex),
Rating: x out of 5 (regex)

GPU Filter:
Include: RTX, GTX, GeForce, NVIDIA, Radeon, RX, AMD Radeon,
Exclude: Intel, UHD, Iris, Integrated, UMA, Shared, Arc,


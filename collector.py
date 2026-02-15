# collector.py
import time
import urllib.parse
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from ocr_mongo import ocr_and_store 


def is_blocked(page_source: str) -> bool:
    s = (page_source or "").lower()
    needles = [
        "robot check",
        "enter the characters you see below",
        "/errors/validatecaptcha",
        "sorry, we just need to make sure you're not a robot",
    ]
    return any(n in s for n in needles)


def accept_cookies(driver):
    for sel in ["#sp-cc-accept", "input#sp-cc-accept", "button[name='accept']"]:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            if btn.is_displayed():
                btn.click()
                time.sleep(0.5)
                return True
        except Exception:
            pass
    return False


def goto_next(driver):
    nxt = driver.find_element(By.CSS_SELECTOR, "a.s-pagination-next")
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", nxt)
    time.sleep(0.4)
    nxt.click()


def collect_cards_streaming_to_mongo(
    query: str,
    max_pages: int,
    cards_per_page: int,
    base_dir: Path,
    headless: bool = False,
    wait_seconds: int = 25,
):
    """
    Streaming pipeline:
    Selenium -> screenshot -> OCR -> MongoDB (upsert) immediately
    Returns list of stored docs (only those that passed filters).
    """

    card_dir = base_dir / "card_images"
    debug_dir = base_dir / "output" / "debug"
    card_dir.mkdir(parents=True, exist_ok=True)
    debug_dir.mkdir(parents=True, exist_ok=True)

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    if headless:
        options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, wait_seconds)

    stored_docs = []

    try:
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.amazon.in/s?k={encoded}"
        print("Opening:", url)

        driver.get(url)
        time.sleep(1)
        accept_cookies(driver)

        for page in range(1, max_pages + 1):
            print(f"\n=== PAGE {page} ===")

            if is_blocked(driver.page_source):
                (debug_dir / f"BLOCKED_page{page:02d}.html").write_text(driver.page_source, encoding="utf-8")
                driver.save_screenshot(str(debug_dir / f"BLOCKED_page{page:02d}.png"))
                print("[STOP] Block/CAPTCHA detected. Saved debug files.")
                break

            try:
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.s-result-item[data-component-type='s-search-result']")
                    )
                )
            except TimeoutException:
                (debug_dir / f"TIMEOUT_page{page:02d}.html").write_text(driver.page_source, encoding="utf-8")
                driver.save_screenshot(str(debug_dir / f"TIMEOUT_page{page:02d}.png"))
                print("[STOP] Timeout waiting for results. Saved debug files.")
                break

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.25);")
            time.sleep(1)

            cards = driver.find_elements(By.CSS_SELECTOR, "div.s-result-item[data-component-type='s-search-result']")
            print("Cards found:", len(cards))

            saved = 0
            for _, card in enumerate(cards):
                if saved >= cards_per_page:
                    break

                asin = (card.get_attribute("data-asin") or "").strip()
                if not asin:
                    continue

                img_path = card_dir / f"card_p{page:02d}_{saved:02d}_{asin}.png"

                try:
                    card.screenshot(str(img_path))
                except Exception:
                    continue

                
                doc = ocr_and_store(
                    image_path=str(img_path),
                    asin=asin,
                    page=page,
                    index=saved,
                    query=query,
                )

                if doc:
                    stored_docs.append(doc)
                    print(f" Mongo saved: {doc['title'][:60]} | {doc.get('price','')} | {doc.get('rating','')}")
                else:
                    print(" -> skipped by OCR filters")

                saved += 1

            print("Processed cards:", saved)

            if page < max_pages:
                try:
                    goto_next(driver)
                    time.sleep(2.5)
                except Exception:
                    print("[END] Next not clickable / last page.")
                    break

    finally:
        driver.quit()

    return stored_docs


if __name__ == "__main__":
    out = collect_cards_streaming_to_mongo(
        query="gaming laptop",
        max_pages=2,
        cards_per_page=12,
        base_dir=Path(__file__).parent,
        headless=False,
    )

    print("\nStored to MongoDB:", len(out))

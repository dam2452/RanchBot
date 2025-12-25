from typing import Optional

from playwright.sync_api import sync_playwright


class ScraperClipboard:
    @staticmethod
    def scrape(url: str, headless: bool = True) -> Optional[str]:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=headless)
                context = browser.new_context()
                page = context.new_page()

                page.goto(url, wait_until="networkidle", timeout=30000)

                page.keyboard.press("Control+A")
                page.keyboard.press("Control+C")

                clipboard_text = page.evaluate("navigator.clipboard.readText()")

                browser.close()
                return clipboard_text

        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Clipboard scraping failed: {e}")
            return None

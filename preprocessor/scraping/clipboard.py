import logging
from typing import Optional

from patchright.sync_api import sync_playwright

logger = logging.getLogger(__name__)


class ScraperClipboard:
    @staticmethod
    def scrape(url: str, headless: bool = True) -> Optional[str]:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=headless,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                    ],
                )
                context = browser.new_context()
                page = context.new_page()

                page.goto(url, wait_until="networkidle", timeout=30000)

                page.keyboard.press("Control+A")
                page.keyboard.press("Control+C")

                clipboard_text = page.evaluate("navigator.clipboard.readText()")

                browser.close()
                return clipboard_text

        except Exception as e:
            logger.error(f"Clipboard scraping failed: {e}")
            return None

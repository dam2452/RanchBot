from typing import (
    List,
    Optional,
)

from patchright.sync_api import sync_playwright

from preprocessor.lib.core.logging import ErrorHandlingLogger


class ScraperClipboard:
    _BROWSER_ARGS: List[str] = ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']

    @staticmethod
    def scrape(url: str, headless: bool=True, logger: Optional[ErrorHandlingLogger]=None) -> Optional[str]:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=headless, args=ScraperClipboard._BROWSER_ARGS)
                context = browser.new_context()
                page = context.new_page()
                page.goto(url, wait_until='networkidle', timeout=30000)
                page.keyboard.press('Control+A')
                page.keyboard.press('Control+C')
                clipboard_text = page.evaluate('navigator.clipboard.readText()')
                browser.close()
                return clipboard_text
        except Exception as e:
            if logger:
                logger.error(f'Clipboard scraping failed: {e}')
            return None

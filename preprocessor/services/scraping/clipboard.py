from typing import Optional

from patchright.sync_api import sync_playwright

from preprocessor.services.core.logging import ErrorHandlingLogger


class ScraperClipboard:
    __BROWSER_ARGS = ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']

    @staticmethod
    def scrape(url: str, headless: bool = True, logger: Optional[ErrorHandlingLogger] = None) -> Optional[str]:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=headless, args=ScraperClipboard.__BROWSER_ARGS)
                context = browser.new_context()
                page = context.new_page()

                page.goto(url, wait_until='networkidle', timeout=30000)

                page.keyboard.press('Control+A')
                page.keyboard.press('Control+C')

                content = page.evaluate('navigator.clipboard.readText()')
                browser.close()
                return content
        except Exception as e:
            if logger:
                logger.error(f'Clipboard scraping failed for {url}: {e}')
            return None

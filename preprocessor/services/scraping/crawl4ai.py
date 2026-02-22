import asyncio
from pathlib import Path
from typing import Optional

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import (
    BrowserConfig,
    CrawlerRunConfig,
)
from pathvalidate import sanitize_filename
import ua_generator

from preprocessor.services.core.logging import ErrorHandlingLogger


class ScraperCrawl4AI:
    @staticmethod
    def scrape(
            url: str,
            save_markdown: bool = False,
            output_dir: Optional[Path] = None,
            logger: Optional[ErrorHandlingLogger] = None,
    ) -> Optional[str]:
        return asyncio.run(ScraperCrawl4AI.__scrape_async(url, save_markdown, output_dir, logger))

    @staticmethod
    async def __scrape_async(
            url: str,
            save_markdown: bool,
            output_dir: Optional[Path],
            logger: Optional[ErrorHandlingLogger],
    ) -> Optional[str]:
        try:
            browser_config = BrowserConfig(
                headless=True,
                enable_stealth=True,
                viewport_width=1920,
                viewport_height=1080,
                user_agent=str(ua_generator.generate()),
            )
            run_config = CrawlerRunConfig(wait_until='networkidle', page_timeout=60000, delay_before_return_html=2.0)

            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=run_config)
                if result.success:
                    if save_markdown and output_dir:
                        ScraperCrawl4AI.__persist_markdown(result.markdown, url, output_dir, logger)
                    return result.markdown

                if logger:
                    logger.error(f'Crawl4AI failed for {url}: {result.error_message}')
        except Exception as e:
            if logger:
                logger.error(f'Crawl4AI exception: {e}')
        return None

    @staticmethod
    def __persist_markdown(content: str, url: str, output_dir: Path, logger: Optional[ErrorHandlingLogger]) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_name = sanitize_filename(url.replace('://', '_').replace('/', '_'))
        path = output_dir / f'{safe_name}.md'

        path.write_text(content, encoding='utf-8')
        if logger:
            logger.info(f'Saved markdown: {path}')

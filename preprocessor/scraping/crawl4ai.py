import asyncio
import logging
from pathlib import Path
from typing import Optional

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import (
    BrowserConfig,
    CrawlerRunConfig,
)
from pathvalidate import sanitize_filename
import ua_generator

logger = logging.getLogger(__name__)


class ScraperCrawl4AI:
    @staticmethod
    def scrape(url: str, save_markdown: bool = False, output_dir: Optional[Path] = None) -> Optional[str]:
        return asyncio.run(ScraperCrawl4AI.__scrape_async(url, save_markdown, output_dir))

    @staticmethod
    def __sanitize_url_to_filename(url: str) -> str:
        return sanitize_filename(url.replace("://", "_").replace("/", "_"))

    @staticmethod
    def __save_markdown(content: str, url: str, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = ScraperCrawl4AI.__sanitize_url_to_filename(url)
        md_file = output_dir / f"{filename}.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Saved markdown to: {md_file}")

    @staticmethod
    async def __scrape_async(url: str, save_markdown: bool = False, output_dir: Optional[Path] = None) -> Optional[str]:
        try:
            ua = ua_generator.generate()
            browser_config = BrowserConfig(
                headless=True,
                enable_stealth=True,
                viewport_width=1920,
                viewport_height=1080,
                user_agent=str(ua),
            )
            run_config = CrawlerRunConfig(
                wait_until="networkidle",
                page_timeout=60000,
                delay_before_return_html=2.0,
            )

            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=run_config)

                if result.success:
                    if save_markdown and output_dir:
                        ScraperCrawl4AI.__save_markdown(result.markdown, url, output_dir)
                    return result.markdown
                logger.error(f"Crawl4AI failed: {result.error_message}")
                return None

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Crawl4AI error: {e}")
            return None

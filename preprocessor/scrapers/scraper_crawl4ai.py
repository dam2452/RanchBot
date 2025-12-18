import asyncio
from typing import Optional

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import (
    BrowserConfig,
    CrawlerRunConfig,
)


class ScraperCrawl4AI:
    @staticmethod
    async def _scrape_async(url: str, save_markdown: bool = False) -> Optional[str]:
        try:
            browser_config = BrowserConfig(headless=True)
            run_config = CrawlerRunConfig()

            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=run_config)

                if result.success:
                    if save_markdown:
                        safe_name = url.split("/")[-1].replace(":", "_")
                        md_file = f"crawl4ai_output_{safe_name}.md"
                        with open(md_file, "w", encoding="utf-8") as f:
                            f.write(result.markdown)
                        print(f"Saved markdown to: {md_file}")
                    return result.markdown
                print(f"Crawl4AI failed: {result.error_message}")
                return None

        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"Crawl4AI error: {e}")
            return None

    @staticmethod
    def scrape(url: str, save_markdown: bool = False) -> Optional[str]:
        return asyncio.run(ScraperCrawl4AI._scrape_async(url, save_markdown))

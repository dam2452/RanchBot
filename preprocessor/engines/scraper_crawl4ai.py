import asyncio
from typing import Optional

try:
    from crawl4ai import AsyncWebCrawler
    from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False


class ScraperCrawl4AI:
    @staticmethod
    async def _scrape_async(url: str, save_markdown: bool = False) -> Optional[str]:
        if not CRAWL4AI_AVAILABLE:
            print("crawl4ai not installed. Install with: pip install crawl4ai")
            return None

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
                else:
                    print(f"Crawl4AI failed: {result.error_message}")
                    return None

        except Exception as e:
            print(f"Crawl4AI error: {e}")
            return None

    @staticmethod
    def scrape(url: str, save_markdown: bool = False) -> Optional[str]:
        return asyncio.run(ScraperCrawl4AI._scrape_async(url, save_markdown))

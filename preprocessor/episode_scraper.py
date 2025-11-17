import json
import logging
from pathlib import Path
from typing import (
    Dict,
    List,
    Optional,
)

from playwright.sync_api import sync_playwright  # noqa: F401  # pylint: disable=unused-import
from rich.console import Console
from rich.progress import Progress

from preprocessor.engines.scraper_clipboard import ScraperClipboard
from preprocessor.engines.scraper_crawl4ai import ScraperCrawl4AI
from preprocessor.llm_provider import LLMProvider
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger

console = Console()


class EpisodeScraper:
    def __init__(self, args: Dict):
        self.urls: List[str] = args["urls"]
        self.output_file: Path = args["output_file"]
        self.llm_provider: str = args.get("llm_provider", "lmstudio")
        self.llm_api_key: Optional[str] = args.get("llm_api_key")
        self.llm_model: Optional[str] = args.get("llm_model")
        self.headless: bool = args.get("headless", True)
        self.merge_sources: bool = args.get("merge_sources", True)
        self.scraper_method: str = args.get("scraper_method", "crawl4ai")

        self.logger: ErrorHandlingLogger = ErrorHandlingLogger(
            class_name=self.__class__.__name__,
            loglevel=logging.DEBUG,
            error_exit_code=7,
        )

        self.llm: Optional[LLMProvider] = None

    def work(self) -> int:
        try:
            self._exec()
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(f"Episode scraping failed: {e}")
        return self.logger.finalize()

    def _exec(self) -> None:
        self.llm = LLMProvider(
            provider=self.llm_provider,
            api_key=self.llm_api_key,
            model=self.llm_model,
        )

        console.print(f"[blue]Scraping {len(self.urls)} URLs...[/blue]")

        scraped_data = []
        with Progress() as progress:
            task = progress.add_task("[cyan]Scraping pages...", total=len(self.urls))

            for url in self.urls:
                try:
                    page_text = self._scrape_url(url)
                    if page_text:
                        season_data = self.llm.extract_season_episodes(page_text, url)
                        if season_data:
                            scraped_data.append({
                                "url": url,
                                "season_data": season_data,
                            })
                            console.print(f"[green]✓[/green] {url}: Season {season_data.season_number} ({len(season_data.episodes)} episodes)")
                        else:
                            self.logger.error(f"Failed to extract season data from {url}")
                    else:
                        self.logger.error(f"Failed to scrape {url}")
                except Exception as e:  # pylint: disable=broad-exception-caught
                    self.logger.error(f"Error processing {url}: {e}")
                finally:
                    progress.advance(task)

        if not scraped_data:
            console.print("[yellow]No data scraped[/yellow]")
            return

        console.print(f"[blue]Scraped {len(scraped_data)} pages successfully[/blue]")

        if len(scraped_data) == 1:
            result = scraped_data[0]["season_data"].model_dump()
        else:
            result = {
                "sources": [item["url"] for item in scraped_data],
                "seasons": [item["season_data"].model_dump() for item in scraped_data],
            }

        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        console.print(f"[green]✓ Saved to: {self.output_file}[/green]")

    def _scrape_url(self, url: str) -> Optional[str]:
        console.print(f"[cyan]Scraping method: {self.scraper_method}[/cyan]")

        if self.scraper_method == "clipboard":
            return ScraperClipboard.scrape(url, headless=self.headless)
        if self.scraper_method == "crawl4ai":
            return ScraperCrawl4AI.scrape(url, save_markdown=True)
        self.logger.error(f"Unknown scraper method: {self.scraper_method}")
        return None

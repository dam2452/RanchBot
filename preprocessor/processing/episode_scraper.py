import json
import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from playwright.sync_api import sync_playwright  # noqa: F401  # pylint: disable=unused-import
from rich.progress import Progress

from preprocessor.providers.llm import LLMProvider
from preprocessor.scrapers.scraper_clipboard import ScraperClipboard
from preprocessor.scrapers.scraper_crawl4ai import ScraperCrawl4AI
from preprocessor.utils.console import console
from preprocessor.utils.error_handling_logger import ErrorHandlingLogger


class EpisodeScraper:
    def __init__(self, args: Dict[str, Any]):
        self.urls: List[str] = args["urls"]
        self.output_file: Path = args["output_file"]
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
            self.__exec()
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(f"Episode scraping failed: {e}")
        return self.logger.finalize()

    def __exec(self) -> None:
        self.llm = LLMProvider()

        console.print(f"[blue]Scraping {len(self.urls)} URLs...[/blue]")

        scraped_pages = []
        with Progress() as progress:
            task = progress.add_task("[cyan]Fetching pages...", total=len(self.urls))

            for url in self.urls:
                try:
                    page_text = self.__scrape_url(url)
                    if page_text:
                        scraped_pages.append({
                            "url": url,
                            "markdown": page_text,
                        })
                        console.print(f"[green]✓[/green] {url}: {len(page_text)} chars")
                    else:
                        self.logger.error(f"Failed to scrape {url}")
                except Exception as e:  # pylint: disable=broad-exception-caught
                    self.logger.error(f"Error scraping {url}: {e}")
                finally:
                    progress.advance(task)

        if not scraped_pages:
            console.print("[yellow]No pages scraped[/yellow]")
            return

        console.print(f"[blue]Scraped {len(scraped_pages)} pages, sending to LLM...[/blue]")

        try:
            all_seasons = self.llm.extract_all_seasons(scraped_pages)
            if not all_seasons:
                self.logger.error("LLM failed to extract any season data")
                return

            result = {
                "sources": [item["url"] for item in scraped_pages],
                "seasons": [season.model_dump() for season in all_seasons],
            }

            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            total_episodes = sum(len(season.episodes) for season in all_seasons)
            console.print(f"[green]✓ Extracted {len(all_seasons)} seasons, {total_episodes} episodes[/green]")
            console.print(f"[green]✓ Saved to: {self.output_file}[/green]")

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(f"LLM extraction failed: {e}")

    def __scrape_url(self, url: str) -> Optional[str]:
        console.print(f"[cyan]Scraping method: {self.scraper_method}[/cyan]")

        if self.scraper_method == "clipboard":
            return ScraperClipboard.scrape(url, headless=self.headless)
        if self.scraper_method == "crawl4ai":
            return ScraperCrawl4AI.scrape(url, save_markdown=False)
        self.logger.error(f"Unknown scraper method: {self.scraper_method}")
        return None

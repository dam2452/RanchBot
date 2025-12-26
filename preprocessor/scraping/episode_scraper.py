import json
import logging
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
)

from playwright.sync_api import sync_playwright  # noqa: F401  # pylint: disable=unused-import

from preprocessor.config.config import settings
from preprocessor.core.base_processor import BaseProcessor
from preprocessor.core.enums import ScraperMethod
from preprocessor.providers.llm import LLMProvider
from preprocessor.scraping.clipboard import ScraperClipboard
from preprocessor.scraping.crawl4ai import ScraperCrawl4AI
from preprocessor.utils.console import (
    console,
    create_progress,
)

if TYPE_CHECKING:
    from rich.progress import Progress


class EpisodeScraper(BaseProcessor):
    def __init__(self, args: Dict[str, Any]):
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=7,
            loglevel=logging.DEBUG,
        )

        self.urls: List[str] = self._args["urls"]
        self.output_file: Path = self._args["output_file"]
        self.headless: bool = self._args.get("headless", True)
        self.merge_sources: bool = self._args.get("merge_sources", True)

        scraper_method_str = self._args.get("scraper_method", "crawl4ai")
        self.scraper_method = ScraperMethod(scraper_method_str)

        self.llm: Optional[LLMProvider] = None

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if "urls" not in args or not args["urls"]:
            raise ValueError("At least one URL is required")
        if "output_file" not in args:
            raise ValueError("output_file is required")

    def _execute(self) -> None:
        self.llm = LLMProvider()

        console.print(f"[blue]Scraping {len(self.urls)} URLs...[/blue]")

        scraped_pages = []
        try:
            with create_progress() as progress:
                task = progress.add_task("Fetching pages", total=len(self.urls))

                for url in self.urls:
                    try:
                        page_text = self._scrape_url(url, progress)
                        if page_text:
                            scraped_pages.append({
                                "url": url,
                                "markdown": page_text,
                            })
                            progress.console.print(f"[green]✓[/green] {url}: {len(page_text)} chars")
                        else:
                            self.logger.error(f"Failed to scrape {url}")
                    except Exception as e:  # pylint: disable=broad-exception-caught
                        self.logger.error(f"Error scraping {url}: {e}")
                    finally:
                        progress.advance(task)
        except KeyboardInterrupt:
            console.print("\n[yellow]Scraping interrupted[/yellow]")
            raise

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

    def _scrape_url(self, url: str, progress: "Progress") -> Optional[str]:
        progress.console.print(f"[cyan]Scraping method: {self.scraper_method.value}[/cyan]")

        if self.scraper_method == ScraperMethod.CLIPBOARD:
            return ScraperClipboard.scrape(url, headless=self.headless)
        if self.scraper_method == ScraperMethod.CRAWL4AI:
            return ScraperCrawl4AI.scrape(url, save_markdown=True, output_dir=settings.scraper.output_dir)
        self.logger.error(f"Unknown scraper method: {self.scraper_method}")
        return None

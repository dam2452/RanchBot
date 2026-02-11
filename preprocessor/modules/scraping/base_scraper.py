from abc import abstractmethod
import json
import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from preprocessor.config.config import settings
from preprocessor.config.enums import (
    ParserMode,
    ScraperMethod,
)
from preprocessor.lib.ai import LLMProvider
from preprocessor.lib.scraping.clipboard import ScraperClipboard
from preprocessor.lib.scraping.crawl4ai import ScraperCrawl4AI
from preprocessor.lib.ui.console import console
from preprocessor.modules.base_processor import BaseProcessor


class BaseScraper(BaseProcessor):

    def __init__(self, args: Dict[str, Any], error_exit_code: int=7):
        super().__init__(args=args, class_name=self.__class__.__name__, error_exit_code=error_exit_code, loglevel=logging.DEBUG)
        self.urls: List[str] = self._args['urls']
        self.output_file: Path = self._args['output_file']
        self.headless: bool = self._args.get('headless', True)
        scraper_method_str = self._args.get('scraper_method', 'crawl4ai')
        self.scraper_method = ScraperMethod(scraper_method_str)
        parser_mode_str = self._args.get('parser_mode', 'normal')
        self.parser_mode = ParserMode(parser_mode_str)
        self.llm: Optional[LLMProvider] = None

    def get_output_subdir(self) -> str:
        return ""

    def _execute(self) -> None:
        self.llm = LLMProvider(parser_mode=self.parser_mode)
        console.print(f'[blue]Scraping {len(self.urls)} URLs...[/blue]')
        scraped_pages = self.__scrape_all_urls()
        if not scraped_pages:
            console.print('[yellow]No pages scraped[/yellow]')
            return
        console.print(f'[blue]Scraped {len(scraped_pages)} pages, processing with LLM...[/blue]')
        try:
            self._process_scraped_pages(scraped_pages)
        except Exception as e:
            self.logger.error(f'LLM processing failed: {e}')

    @abstractmethod
    def _process_scraped_pages(self, scraped_pages: List[Dict[str, Any]]) -> None:
        pass

    def _save_result(self, result: Dict[str, Any]) -> None:
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if 'urls' not in args or not args['urls']:
            raise ValueError('At least one URL is required')
        if 'output_file' not in args:
            raise ValueError('output_file is required')

    def __scrape_all_urls(self) -> List[Dict[str, Any]]:
        scraped_pages = []
        try:
            for i, url in enumerate(self.urls, 1):
                console.print(f'[cyan]Fetching page {i}/{len(self.urls)}[/cyan]')
                try:
                    page_text = self.__scrape_url(url)
                    if page_text:
                        scraped_pages.append({'url': url, 'markdown': page_text})
                        console.print(f'[green]✓[/green] {url}: {len(page_text)} chars')
                    else:
                        self.logger.error(f'Failed to scrape {url}')
                except Exception as e:
                    self.logger.error(f'Error scraping {url}: {e}')
        except KeyboardInterrupt:
            console.print('\n[yellow]Scraping interrupted[/yellow]')
            raise
        return scraped_pages

    def __scrape_url(self, url: str) -> Optional[str]:
        console.print(f'[cyan]Scraping method: {self.scraper_method.value}[/cyan]')
        if self.scraper_method == ScraperMethod.CLIPBOARD:
            return ScraperClipboard.scrape(url, headless=self.headless, logger=self.logger)
        if self.scraper_method == ScraperMethod.CRAWL4AI:
            return ScraperCrawl4AI.scrape(url, save_markdown=True, output_dir=settings.scraper.get_output_dir(self.series_name), logger=self.logger)
        self.logger.error(f'Unknown scraper method: {self.scraper_method}')
        return None

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

from preprocessor.config.enums import (
    ParserMode,
    ScraperMethod,
)
from preprocessor.config.settings_instance import settings
from preprocessor.services.ai import LLMProvider
from preprocessor.services.core.base_processor import (
    BaseProcessor,
    OutputSpec,
    ProcessingItem,
)
from preprocessor.services.scraping.clipboard import ScraperClipboard
from preprocessor.services.scraping.crawl4ai import ScraperCrawl4AI
from preprocessor.services.ui.console import console


class BaseScraper(BaseProcessor):
    def __init__(self, args: Dict[str, Any], error_exit_code: int = 7) -> None:
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=error_exit_code,
            loglevel=logging.DEBUG,
        )
        self.__urls: List[str] = self._args['urls']
        self.__output_file: Path = self._args['output_file']
        self.__headless: bool = self._args.get('headless', True)
        self.__scraper_method = ScraperMethod(self._args.get('scraper_method', 'crawl4ai'))
        self.__parser_mode = ParserMode(self._args.get('parser_mode', 'normal'))
        self.__llm: Optional[LLMProvider] = None

    @property
    def output_file(self) -> Path:
        return self.__output_file

    @property
    def llm(self) -> LLMProvider:
        if self.__llm is None:
            raise RuntimeError("LLMProvider not initialized. Call _execute first.")
        return self.__llm

    def _execute(self) -> None:
        self.__llm = LLMProvider(parser_mode=self.__parser_mode)
        console.print(f'[blue]Scraping {len(self.__urls)} URLs...[/blue]')

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
        self.__output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.__output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

    def __scrape_all_urls(self) -> List[Dict[str, Any]]:
        results = []
        for i, url in enumerate(self.__urls, 1):
            console.print(f'[cyan]Fetching page {i}/{len(self.__urls)}[/cyan]')
            try:
                content = self.__run_scraper(url)
                if content:
                    results.append({'url': url, 'markdown': content})
                    console.print(f'[green]Success[/green] {url}: {len(content)} chars')
                else:
                    self.logger.error(f'Failed to scrape {url}')
            except Exception as e:
                self.logger.error(f'Error scraping {url}: {e}')
        return results

    def __run_scraper(self, url: str) -> Optional[str]:
        if self.__scraper_method == ScraperMethod.CLIPBOARD:
            return ScraperClipboard.scrape(url, headless=self.__headless, logger=self.logger)

        if self.__scraper_method == ScraperMethod.CRAWL4AI:
            return ScraperCrawl4AI.scrape(
                url,
                save_markdown=True,
                output_dir=settings.scraper.get_output_dir(self.series_name),
                logger=self.logger,
            )

        return None

    def get_output_subdir(self) -> str:
        return 'scraper'

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        return []

    def _get_processing_items(self) -> List[ProcessingItem]:
        return []

    def _process_item(
            self, item: ProcessingItem, missing_outputs: List[OutputSpec],
    ) -> None:
        pass

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if 'urls' not in args:
            raise ValueError("Missing required argument: 'urls'")
        if 'output_file' not in args:
            raise ValueError("Missing required argument: 'output_file'")

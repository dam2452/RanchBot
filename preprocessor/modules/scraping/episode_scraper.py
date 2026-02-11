from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from preprocessor.lib.ui.console import console
from preprocessor.modules.scraping.base_scraper import BaseScraper


class EpisodeScraper(BaseScraper):

    def __init__(self, args: Dict[str, Any]) -> None:
        super().__init__(args)
        self.merge_sources: bool = self._args.get('merge_sources', True)
        self.expected_episodes_count: Optional[int] = self._args.get('expected_episodes_count')
        self.videos_dir: Optional[Path] = self._args.get('videos_dir')

    def _process_scraped_pages(self, scraped_pages: List[Dict[str, Any]]) -> None:
        all_seasons = self.llm.extract_all_seasons(scraped_pages)
        if not all_seasons:
            self.logger.error('LLM failed to extract any season data')
            return
        result = {'sources': [item['url'] for item in scraped_pages], 'seasons': [season.model_dump() for season in all_seasons]}
        self._save_result(result)
        total_episodes = sum((len(season.episodes) for season in all_seasons))
        console.print(f'[green]✓ Extracted {len(all_seasons)} seasons, {total_episodes} episodes[/green]')
        console.print(f'[green]✓ Saved to: {self.output_file}[/green]')
        self.__validate_and_report_coverage(total_episodes)

    def __count_video_files(self, directory: Path) -> int:
        count = 0
        for ext in self.SUPPORTED_VIDEO_EXTENSIONS:
            count += len(list(directory.rglob(f'*{ext}')))
        return count

    @staticmethod
    def __get_coverage_status(scraped: int, expected: int) -> Tuple[str, str]:
        if scraped < expected:
            return 'missing', f'Missing {expected - scraped} episodes'
        if scraped > expected:
            return 'extra', f'Scraped {scraped - expected} more episodes than video files'
        return 'perfect', 'Perfect coverage'

    def __get_expected_episodes_count(self) -> Optional[int]:
        if self.expected_episodes_count is not None:
            return self.expected_episodes_count
        if self.videos_dir and self.videos_dir.exists():
            return self.__count_video_files(self.videos_dir)
        return None

    @staticmethod
    def __print_coverage_report(scraped: int, expected: int, status: str, message: str) -> None:
        coverage_pct = scraped / expected * 100 if expected > 0 else 0
        console.print('\n[yellow]⚠ Episode coverage validation:[/yellow]')
        console.print(f'  [cyan]Scraped episodes: {scraped}[/cyan]')
        console.print(f'  [cyan]Video files found: {expected}[/cyan]')
        console.print(f'  [cyan]Coverage: {coverage_pct:.1f}%[/cyan]')
        if status == 'missing':
            console.print(f'\n[red]✗ WARNING: {message}![/red]')
            console.print('  [yellow]Consider adding more URLs to --scrape-urls[/yellow]')
            console.print('  [dim]Not all video files will have metadata available[/dim]\n')
        elif status == 'extra':
            console.print(f'\n[yellow]⚠ Note: {message}[/yellow]')
            console.print('  [dim]This is OK if you plan to add more videos later[/dim]\n')
        else:
            console.print('\n[green]✓ Perfect coverage - all video files have metadata![/green]\n')

    @staticmethod
    def __print_no_validation_warning(scraped_count: int) -> None:
        console.print('\n[yellow]⚠ Coverage validation:[/yellow]')
        console.print(f'  [cyan]Scraped episodes: {scraped_count}[/cyan]')
        console.print('  [yellow]No video directory provided - unable to validate coverage[/yellow]')
        console.print('  [dim]Make sure the scraped episodes cover all your video files[/dim]')
        console.print('  [dim]You can add more --scrape-urls if needed[/dim]\n')

    def __validate_and_report_coverage(self, scraped_episodes_count: int) -> None:
        expected_count = self.__get_expected_episodes_count()
        if expected_count is None:
            self.__print_no_validation_warning(scraped_episodes_count)
            return
        status, message = self.__get_coverage_status(scraped_episodes_count, expected_count)
        self.__print_coverage_report(scraped_episodes_count, expected_count, status, message)

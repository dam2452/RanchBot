from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from patchright.sync_api import sync_playwright  # noqa: F401  # pylint: disable=unused-import

from preprocessor.scraping.base_scraper import BaseScraper
from preprocessor.utils.console import console
from preprocessor.utils.file_utils import atomic_write_json


class EpisodeScraper(BaseScraper):
    def __init__(self, args: Dict[str, Any]):
        super().__init__(args)
        self.merge_sources: bool = self._args.get("merge_sources", True)
        self.expected_episodes_count: Optional[int] = self._args.get("expected_episodes_count")
        self.videos_dir: Optional[Path] = self._args.get("videos_dir")

    def _process_scraped_pages(self, scraped_pages: List[Dict[str, Any]]) -> None:
        all_seasons = self.llm.extract_all_seasons(scraped_pages)
        if not all_seasons:
            self.logger.error("LLM failed to extract any season data")
            return

        result = {
            "sources": [item["url"] for item in scraped_pages],
            "seasons": [season.model_dump() for season in all_seasons],
        }

        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.output_file, result, indent=2, ensure_ascii=False)

        total_episodes = sum(len(season.episodes) for season in all_seasons)
        console.print(f"[green]✓ Extracted {len(all_seasons)} seasons, {total_episodes} episodes[/green]")
        console.print(f"[green]✓ Saved to: {self.output_file}[/green]")

        self._validate_episode_coverage(total_episodes)

    def _validate_episode_coverage(self, scraped_episodes_count: int) -> None:
        expected_count = self._get_expected_episodes_count()

        if expected_count is None:
            console.print("\n[yellow]⚠ Coverage validation:[/yellow]")
            console.print(f"  [cyan]Scraped episodes: {scraped_episodes_count}[/cyan]")
            console.print("  [yellow]No video directory provided - unable to validate coverage[/yellow]")
            console.print("  [dim]Make sure the scraped episodes cover all your video files[/dim]")
            console.print("  [dim]You can add more --scrape-urls if needed[/dim]\n")
            return

        coverage_percentage = (scraped_episodes_count / expected_count * 100) if expected_count > 0 else 0

        console.print("\n[yellow]⚠ Episode coverage validation:[/yellow]")
        console.print(f"  [cyan]Scraped episodes: {scraped_episodes_count}[/cyan]")
        console.print(f"  [cyan]Video files found: {expected_count}[/cyan]")
        console.print(f"  [cyan]Coverage: {coverage_percentage:.1f}%[/cyan]")

        if scraped_episodes_count < expected_count:
            console.print(f"\n[red]✗ WARNING: Missing {expected_count - scraped_episodes_count} episodes![/red]")
            console.print("  [yellow]Consider adding more URLs to --scrape-urls[/yellow]")
            console.print("  [dim]Not all video files will have metadata available[/dim]\n")
        elif scraped_episodes_count > expected_count:
            console.print(f"\n[yellow]⚠ Note: Scraped {scraped_episodes_count - expected_count} more episodes than video files[/yellow]")
            console.print("  [dim]This is OK if you plan to add more videos later[/dim]\n")
        else:
            console.print("\n[green]✓ Perfect coverage - all video files have metadata![/green]\n")

    def _get_expected_episodes_count(self) -> Optional[int]:
        if self.expected_episodes_count is not None:
            return self.expected_episodes_count

        if self.videos_dir and self.videos_dir.exists():
            return self._count_video_files(self.videos_dir)

        return None

    def _count_video_files(self, directory: Path) -> int:
        count = 0
        for ext in self.SUPPORTED_VIDEO_EXTENSIONS:
            count += len(list(directory.rglob(f"*{ext}")))
        return count

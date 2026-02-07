from pathlib import Path
import sys
from typing import Tuple

import click

from preprocessor.scraping.episode_scraper import EpisodeScraper


@click.command(name="scrape-episodes", context_settings={"show_default": True})
@click.option(
    "--urls",
    multiple=True,
    required=True,
    help="URL to scrape (specify multiple times for multiple sources)",
)
@click.option(
    "--output-file",
    type=click.Path(path_type=Path),
    required=True,
    help="Output JSON file path",
)
@click.option(
    "--headless/--no-headless",
    default=True,
    help="Run browser in headless mode",
)
@click.option(
    "--merge-sources/--no-merge",
    default=True,
    help="Merge data from multiple sources",
)
@click.option(
    "--videos-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory containing video files for coverage validation",
)
@click.option(
    "--parser-mode",
    type=click.Choice(["normal", "premium"], case_sensitive=False),
    default="normal",
    help="Parser mode: normal (Qwen local model) or premium (Gemini 2.5 Flash)",
)
def scrape_episodes(
    urls: Tuple[str, ...],
    output_file: Path,
    headless: bool,
    merge_sources: bool,
    videos_dir: Path,
    parser_mode: str,
):
    """Scrape episode metadata from websites."""
    scraper = EpisodeScraper(
        {
            "urls": list(urls),
            "output_file": output_file,
            "headless": headless,
            "merge_sources": merge_sources,
            "videos_dir": videos_dir,
            "parser_mode": parser_mode,
        },
    )

    exit_code = scraper.work()
    sys.exit(exit_code)

from pathlib import Path
import sys

import click

from preprocessor.scraping.episode_scraper import EpisodeScraper


@click.command(name="scrape-episodes")
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
    help="Output JSON file path (required)",
)
@click.option(
    "--headless/--no-headless",
    default=True,
    help="Run browser in headless mode (default: enabled)",
)
@click.option(
    "--merge-sources/--no-merge",
    default=True,
    help="Merge data from multiple sources (default: enabled)",
)
def scrape_episodes(
    urls: tuple,
    output_file: Path,
    headless: bool,
    merge_sources: bool,
):
    """Scrape episode metadata from websites."""
    scraper = EpisodeScraper(
        {
            "urls": list(urls),
            "output_file": output_file,
            "headless": headless,
            "merge_sources": merge_sources,
        },
    )

    exit_code = scraper.work()
    sys.exit(exit_code)

import json
from pathlib import Path
import sys
from unittest.mock import (
    MagicMock,
    patch,
)

import pytest

from preprocessor.processing.episode_scraper import EpisodeScraper
from preprocessor.providers.llm_provider import EpisodeMetadata

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

OUTPUT_FILE = Path(__file__).parent / "output" / "scraped_metadata.json"

MOCK_PAGE_TEXT = """
Ranczo - Sezon 1, Odcinek 13

Tytuł: Testowy Odcinek

Data premiery: 2006-06-05

Widownia: 5000000 widzów

Opis odcinka:
To jest testowy odcinek serialu Ranczo. W tym odcinku bohaterowie przeżywają różne przygody
w malowniczej wsi Wilkowyje.

Streszczenie:
Testowy odcinek przedstawia losy mieszkańców Wilkowyj. Lucy Wilska przyjeżdża do wsi
i próbuje wprowadzić nowoczesne zmiany. Mieszkańcy są sceptyczni wobec jej pomysłów.
Mimo początkowych trudności, Lucy stopniowo zyskuje zaufanie lokalnej społeczności.
Odcinek kończy się uroczystością wiejską, podczas której wszyscy się integrują.
"""


@pytest.fixture(autouse=True)
def mock_crawl4ai_scraper():
    with patch('preprocessor.processing.episode_scraper.Crawl4AIScraper') as mock_scraper_class:
        mock_scraper = MagicMock()
        mock_scraper.scrape.return_value = MOCK_PAGE_TEXT
        mock_scraper_class.return_value = mock_scraper
        yield mock_scraper_class


@pytest.fixture(autouse=True)
def mock_llm_provider():
    with patch('preprocessor.processing.episode_scraper.LLMProvider') as mock_llm_class:
        mock_llm = MagicMock()

        mock_metadata = EpisodeMetadata(
            title="Testowy Odcinek",
            description="To jest testowy odcinek serialu Ranczo.",
            summary="Lucy Wilska przyjeżdża do wsi i próbuje wprowadzić zmiany. Mieszkańcy są sceptyczni.",
            season=1,
            episode_number=13,
        )

        mock_llm.extract_episode_metadata.return_value = mock_metadata
        mock_llm.merge_episode_data.return_value = mock_metadata
        mock_llm_class.return_value = mock_llm

        yield mock_llm_class


@pytest.mark.scraping
def test_episode_scraping():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    scraper = EpisodeScraper({
        "urls": ["https://example.com/episode1", "https://example.com/episode2"],
        "output_file": OUTPUT_FILE,
        "merge_sources": True,
        "scraper_method": "crawl4ai",
    })

    exit_code = scraper.work()
    assert exit_code == 0, "Episode scraping failed"

    assert OUTPUT_FILE.exists(), f"Output file not created: {OUTPUT_FILE}"

    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "sources" in data, "Missing 'sources' in output"
    assert len(data["sources"]) == 2, f"Expected 2 sources, got {len(data['sources'])}"

    for source in data["sources"]:
        assert "url" in source, "Missing 'url' in source"
        assert "metadata" in source or "error" in source, "Missing 'metadata' or 'error' in source"

    if "merged_metadata" in data:
        metadata = data["merged_metadata"]
        assert "title" in metadata, "Missing 'title' in merged metadata"
        assert "description" in metadata, "Missing 'description' in merged metadata"
        assert "summary" in metadata, "Missing 'summary' in merged metadata"

        print("\n✓ Scraped and merged metadata:")
        print(f"  - Title: {metadata['title']}")
        print(f"  - Description: {metadata['description'][:50]}...")
        print(f"  - Summary: {metadata['summary'][:50]}...")
    else:
        assert "metadata_per_source" in data, "Missing metadata in output"
        print(f"\n✓ Scraped {len(data['metadata_per_source'])} sources")


@pytest.mark.scraping
def test_episode_scraping_no_merge():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    scraper = EpisodeScraper({
        "urls": ["https://example.com/episode1"],
        "output_file": OUTPUT_FILE,
        "merge_sources": False,
        "scraper_method": "crawl4ai",
    })

    exit_code = scraper.work()
    assert exit_code == 0, "Episode scraping failed"

    assert OUTPUT_FILE.exists(), f"Output file not created: {OUTPUT_FILE}"

    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "sources" in data, "Missing 'sources' in output"
    assert "metadata_per_source" in data, "Missing 'metadata_per_source' in output"

    print(f"\n✓ Scraped {len(data['metadata_per_source'])} sources without merging")


@pytest.mark.scraping
@pytest.mark.real_scraping
@pytest.mark.skip(reason="Real scraping test - requires Ollama running. Run manually.")
def test_real_episode_scraping():
    real_urls = [
        "https://www.filmweb.pl/serial/Ranczo-2006-276093",
    ]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    scraper = EpisodeScraper({
        "urls": real_urls,
        "output_file": OUTPUT_FILE,
        "merge_sources": False,
        "scraper_method": "crawl4ai",
    })

    exit_code = scraper.work()
    assert exit_code == 0, "Real episode scraping failed"

    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("\n✓ Real scraping results:")
    print(json.dumps(data, indent=2, ensure_ascii=False)[:500])

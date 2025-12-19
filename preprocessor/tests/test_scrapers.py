from pathlib import Path
import sys
from unittest.mock import (
    MagicMock,
    patch,
)

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# pylint: disable=unused-argument,import-outside-toplevel


@pytest.mark.scrapers
def test_scraper_crawl4ai_mock():
    with patch('preprocessor.scrapers.scraper_crawl4ai.AsyncWebCrawler') as mock_crawler_class:
        from preprocessor.scrapers.scraper_crawl4ai import ScraperCrawl4AI

        mock_crawler = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.markdown = "# Test Content\n\nThis is a test."

        async def mock_arun(*_args, **_kwargs):
            return mock_result

        mock_crawler.arun = mock_arun
        mock_crawler.__aenter__ = MagicMock(return_value=mock_crawler)
        mock_crawler.__aexit__ = MagicMock(return_value=None)
        mock_crawler_class.return_value = mock_crawler

        result = ScraperCrawl4AI.scrape("https://example.com")

        assert result == "# Test Content\n\nThis is a test."


@pytest.mark.scrapers
def test_scraper_crawl4ai_failure_mock():
    with patch('preprocessor.scrapers.scraper_crawl4ai.AsyncWebCrawler') as mock_crawler_class:
        from preprocessor.scrapers.scraper_crawl4ai import ScraperCrawl4AI

        mock_crawler = MagicMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_message = "Test error"

        async def mock_arun(*_args, **_kwargs):
            return mock_result

        mock_crawler.arun = mock_arun
        mock_crawler.__aenter__ = MagicMock(return_value=mock_crawler)
        mock_crawler.__aexit__ = MagicMock(return_value=None)
        mock_crawler_class.return_value = mock_crawler

        result = ScraperCrawl4AI.scrape("https://example.com")

        assert result is None


@pytest.mark.scrapers
def test_scraper_clipboard_mock():
    with patch('preprocessor.scrapers.scraper_clipboard.sync_playwright') as mock_playwright:
        from preprocessor.scrapers.scraper_clipboard import ScraperClipboard

        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()

        mock_page.evaluate.return_value = "Test clipboard content"
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser

        result = ScraperClipboard.scrape("https://example.com")

        assert result == "Test clipboard content"
        mock_page.goto.assert_called_once()
        mock_page.keyboard.press.assert_any_call("Control+A")
        mock_page.keyboard.press.assert_any_call("Control+C")


@pytest.mark.scrapers
def test_scraper_clipboard_failure_mock():
    with patch('preprocessor.scrapers.scraper_clipboard.sync_playwright') as mock_playwright:
        from preprocessor.scrapers.scraper_clipboard import ScraperClipboard

        mock_playwright.return_value.__enter__.side_effect = Exception("Test error")

        result = ScraperClipboard.scrape("https://example.com")

        assert result is None


@pytest.mark.scrapers
@pytest.mark.real_scraping
@pytest.mark.skip(reason="Real scraping test. Run manually.")
def test_scraper_crawl4ai_real():
    from preprocessor.scrapers.scraper_crawl4ai import ScraperCrawl4AI

    result = ScraperCrawl4AI.scrape("https://example.com")

    assert result is not None
    assert len(result) > 0
    print(f"\n✓ Crawl4AI scraped {len(result)} characters")


@pytest.mark.scrapers
@pytest.mark.real_scraping
@pytest.mark.skip(reason="Real scraping test. Run manually.")
def test_scraper_clipboard_real():
    from preprocessor.scrapers.scraper_clipboard import ScraperClipboard

    result = ScraperClipboard.scrape("https://example.com", headless=True)

    assert result is not None
    assert len(result) > 0
    print(f"\n✓ Clipboard scraper scraped {len(result)} characters")

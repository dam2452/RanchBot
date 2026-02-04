import logging

import pytest

from bot.services.reindex.series_scanner import SeriesScanner


@pytest.fixture
def logger():
    return logging.getLogger("test")


def test_scan_all_series(logger): # pylint: disable=redefined-outer-name
    scanner = SeriesScanner(logger)
    series = scanner.scan_all_series()

    assert isinstance(series, list)
    if series:
        assert "ranczo" in series


def test_extract_episode_code(logger): # pylint: disable=redefined-outer-name
    scanner = SeriesScanner(logger)

    filename = "ranczo_S01E01.mp4"
    code = scanner._extract_episode_code(filename)
    assert code == "S01E01"

    filename2 = "kiepscy_S10E13.mp4"
    code2 = scanner._extract_episode_code(filename2)
    assert code2 == "S10E13"


def test_scan_series_zips(logger): # pylint: disable=redefined-outer-name
    scanner = SeriesScanner(logger)
    zips = scanner.scan_series_zips("ranczo")

    assert isinstance(zips, list)
    if zips:
        assert all("ranczo" in str(z).lower() for z in zips)


def test_scan_series_mp4s(logger): # pylint: disable=redefined-outer-name
    scanner = SeriesScanner(logger)
    mp4s = scanner.scan_series_mp4s("ranczo")

    assert isinstance(mp4s, dict)
    if mp4s:
        episode_codes = list(mp4s.keys())
        assert all(code.startswith("S") for code in episode_codes)

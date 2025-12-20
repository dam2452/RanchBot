from pathlib import Path
import sys
from unittest.mock import (
    MagicMock,
    patch,
)

import pytest

from preprocessor.providers.llm_provider import (
    EpisodeMetadata,
    LLMProvider,
)

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_llm_provider_initialization():
    with patch('preprocessor.providers.llm_provider.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        provider = LLMProvider(model="test-model")

        assert provider.model == "test-model"
        assert provider.base_url == "http://localhost:11434/v1"
        assert provider.api_key == "ollama"

        mock_openai.assert_called_once()


def test_llm_provider_default_model():
    with patch('preprocessor.providers.llm_provider.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        provider = LLMProvider()

        assert provider.model == "qwen3-coder-50k"
        assert provider.base_url == "http://localhost:11434/v1"
        assert provider.api_key == "ollama"


@pytest.mark.skip(reason="Requires Ollama running. Run manually.")
def test_llm_provider_extract_episode_metadata():
    provider = LLMProvider()

    page_text = """
    Ranczo - Sezon 1, Odcinek 13

    Tytuł: Testowy Odcinek

    Opis: To jest testowy odcinek serialu Ranczo.

    Streszczenie: Lucy Wilska przyjeżdża do wsi i próbuje wprowadzić zmiany.
    """

    metadata = provider.extract_episode_metadata(page_text, "https://example.com")

    assert isinstance(metadata, EpisodeMetadata)
    assert metadata.title
    assert metadata.description
    assert metadata.summary


def test_llm_provider_merge_episode_data_mock():
    with patch('preprocessor.providers.llm_provider.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()

        mock_metadata = {
            "title": "Merged Title",
            "description": "Merged Description",
            "summary": "Merged Summary",
            "season": 1,
            "episode_number": 13,
        }

        mock_message.content = str(mock_metadata)
        mock_choice.message = mock_message
        mock_completion.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai.return_value = mock_client

        provider = LLMProvider()

        metadata_list = [
            EpisodeMetadata(
                title="Title 1",
                description="Description 1",
                summary="Summary 1",
                season=1,
                episode_number=13,
            ),
            EpisodeMetadata(
                title="Title 2",
                description="Description 2",
                summary="Summary 2",
                season=1,
                episode_number=13,
            ),
        ]

        merged = provider.merge_episode_data(metadata_list)

        assert merged is not None
        mock_client.chat.completions.create.assert_called_once()


def test_episode_metadata_creation():
    metadata = EpisodeMetadata(
        title="Test Episode",
        description="This is a test",
        summary="Test summary",
        season=1,
        episode_number=13,
    )

    assert metadata.title == "Test Episode"
    assert metadata.description == "This is a test"
    assert metadata.summary == "Test summary"
    assert metadata.season == 1
    assert metadata.episode_number == 13


def test_episode_metadata_optional_fields():
    metadata = EpisodeMetadata(
        title="Test Episode",
        description="This is a test",
        summary="Test summary",
    )

    assert metadata.title == "Test Episode"
    assert metadata.season is None
    assert metadata.episode_number is None

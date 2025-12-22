from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

import pytest

from preprocessor.providers.llm_provider import EpisodeMetadata, LLMProvider

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_llm_provider_initialization():
    with patch('preprocessor.providers.llm_provider.AutoTokenizer') as mock_tokenizer, \
         patch('preprocessor.providers.llm_provider.AutoModelForCausalLM') as mock_model:

        mock_tokenizer.from_pretrained.return_value = MagicMock()
        mock_model_instance = MagicMock()
        mock_model_instance.device = "cuda:0"
        mock_model.from_pretrained.return_value = mock_model_instance

        provider = LLMProvider(model_name="test-model")

        assert provider.model_name == "test-model"
        mock_tokenizer.from_pretrained.assert_called_once_with("test-model")
        mock_model.from_pretrained.assert_called_once()


def test_llm_provider_default_model():
    with patch('preprocessor.providers.llm_provider.AutoTokenizer') as mock_tokenizer, \
         patch('preprocessor.providers.llm_provider.AutoModelForCausalLM') as mock_model:

        mock_tokenizer.from_pretrained.return_value = MagicMock()
        mock_model_instance = MagicMock()
        mock_model_instance.device = "cuda:0"
        mock_model.from_pretrained.return_value = mock_model_instance

        provider = LLMProvider()

        assert provider.model_name == "Qwen/Qwen2.5-Coder-7B-Instruct"


@pytest.mark.skip(reason="Requires GPU and model download. Run manually.")
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
    with patch('preprocessor.providers.llm_provider.AutoTokenizer') as mock_tokenizer, \
         patch('preprocessor.providers.llm_provider.AutoModelForCausalLM') as mock_model:

        mock_tokenizer_instance = MagicMock()
        mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance

        mock_model_instance = MagicMock()
        mock_model_instance.device = "cuda:0"
        mock_model.from_pretrained.return_value = mock_model_instance

        mock_tokenizer_instance.apply_chat_template.return_value = "mocked prompt"
        mock_tokenizer_instance.return_value = {"input_ids": MagicMock()}
        mock_model_instance.generate.return_value = [[1, 2, 3, 4, 5]]
        mock_tokenizer_instance.decode.return_value = '{"title": "Merged Title", "description": "Merged Description", "summary": "Merged Summary", "season": 1, "episode_number": 13}'

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
        assert merged.title == "Merged Title"


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

import json
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
)

from preprocessor.config.constants import OUTPUT_FILE_NAMES
from preprocessor.config.settings_instance import settings
from preprocessor.services.io.path_service import PathService
from preprocessor.services.validation.file_validators import FileValidator
from preprocessor.services.validation.validators.base_validator import BaseValidator

if TYPE_CHECKING:
    from preprocessor.services.validation.episode_stats import EpisodeStats

ELASTIC_SUBDIRS = settings.output_subdirs.elastic_document_subdirs


class ElasticValidator(BaseValidator):
    def validate(self, stats: 'EpisodeStats') -> None:
        self.__validate_character_detections(stats)
        self.__validate_embeddings(stats)
        self.__validate_elastic_documents(stats)
        self.__validate_text_statistics(stats)

    def __validate_character_detections(self, stats: 'EpisodeStats') -> None:
        char_detections_dir = self.__get_dir(stats, settings.output_subdirs.character_detections)
        detections_file = char_detections_dir / OUTPUT_FILE_NAMES['detections']

        self._validate_json_if_exists(
            stats,
            detections_file,
            error_msg_prefix=f"Invalid {OUTPUT_FILE_NAMES['detections']}",
        )

    def __validate_embeddings(self, stats: 'EpisodeStats') -> None:
        embeddings_dir = self.__get_dir(stats, settings.output_subdirs.embeddings)
        if embeddings_dir.exists():
            embeddings_file = embeddings_dir / OUTPUT_FILE_NAMES['embeddings_text']
            self._validate_json_if_exists(
                stats,
                embeddings_file,
                error_msg_prefix=f"Invalid {OUTPUT_FILE_NAMES['embeddings_text']}",
            )

    def __validate_elastic_documents(self, stats: 'EpisodeStats') -> None:
        subdirs_to_check = [
            ELASTIC_SUBDIRS.text_segments, ELASTIC_SUBDIRS.text_embeddings,
            ELASTIC_SUBDIRS.video_frames, ELASTIC_SUBDIRS.episode_names,
            ELASTIC_SUBDIRS.text_statistics, ELASTIC_SUBDIRS.full_episode_embeddings,
            ELASTIC_SUBDIRS.sound_events, ELASTIC_SUBDIRS.sound_event_embeddings,
        ]

        found_any = False
        elastic_base = settings.output_subdirs.elastic_documents

        for subdir in subdirs_to_check:
            docs_dir = self.__get_dir(stats, f'{elastic_base}/{subdir}')
            if docs_dir.exists():
                found_any = True
                self.__process_jsonl_files(stats, docs_dir, subdir)

        if not found_any:
            self._add_warning(stats, f'Missing {settings.output_subdirs.elastic_documents} directory')

    def __process_jsonl_files(self, stats: 'EpisodeStats', docs_dir: Path, subdir: str) -> None:
        for jsonl_file in docs_dir.glob('*.jsonl'):
            result = FileValidator.validate_jsonl_file(jsonl_file)
            if not result.is_valid:
                self._add_error(stats, f'Invalid JSONL {jsonl_file.name}: {result.error_message}')
            else:
                self.__validate_embedding_dimensions(stats, jsonl_file, subdir)

    def __validate_text_statistics(self, stats: 'EpisodeStats') -> None:
        trans_dir = self.__get_dir(stats, settings.output_subdirs.transcriptions)
        if trans_dir.exists():
            clean_subdir = settings.output_subdirs.transcription_subdirs.clean
            text_stats_file = trans_dir / clean_subdir / f'{stats.series_name}_{stats.episode_info.episode_code()}_text_stats.json'

            if text_stats_file.exists():
                result = FileValidator.validate_json_file(text_stats_file)
                if not result.is_valid:
                    self._add_error(stats, f'Invalid text_stats JSON: {result.error_message}')
            else:
                self._add_warning(stats, f'Missing text statistics file: {text_stats_file.name}')

    def __validate_embedding_dimensions(self, stats: 'EpisodeStats', jsonl_file: Path, subdir: str) -> None:
        embedding_fields = {
            ELASTIC_SUBDIRS.text_embeddings: 'text_embedding',
            ELASTIC_SUBDIRS.video_frames: 'video_embedding',
            ELASTIC_SUBDIRS.episode_names: 'title_embedding',
            ELASTIC_SUBDIRS.full_episode_embeddings: 'full_episode_embedding',
            ELASTIC_SUBDIRS.sound_event_embeddings: 'sound_event_embedding',
        }

        if subdir not in embedding_fields:
            return

        expected_dim = settings.embedding_model.embedding_dim
        field_name = embedding_fields[subdir]

        try:
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    doc = json.loads(line)
                    self.__check_doc_dimension(stats, doc, field_name, expected_dim, jsonl_file.name, line_num)
        except Exception as e:
            self._add_error(stats, f'Error validating embeddings in {jsonl_file.name}: {e}')

    def __check_doc_dimension(
        self, stats: 'EpisodeStats', doc: Dict[str, Any], field: str, expected: int, fname: str,
        lnum: int,
    ) -> None:
        if field in doc and isinstance(doc[field], list):
            actual = len(doc[field])
            if actual != expected:
                self._add_error(stats, f'{fname} line {lnum}: {field} has {actual} dim, expected {expected}')

    def __get_dir(self, stats: 'EpisodeStats', subdir: str) -> Path:
        return PathService(stats.series_name).get_episode_dir(stats.episode_info, subdir)

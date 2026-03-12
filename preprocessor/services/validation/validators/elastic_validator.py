from __future__ import annotations

import json
from pathlib import Path
from typing import (
    Any,
    Dict,
)

from preprocessor.config.output_paths import get_base_output_dir
from preprocessor.config.settings_instance import settings
from preprocessor.services.io.path_service import PathService
from preprocessor.services.validation.episode_stats import EpisodeStats
from preprocessor.services.validation.file_validators import FileValidator
from preprocessor.services.validation.validators.base_validator import BaseValidator

ELASTIC_SUBDIRS = settings.output_subdirs.elastic_document_subdirs


class ElasticValidator(BaseValidator):
    def validate(self, stats: EpisodeStats) -> None:
        self.__validate_character_detections(stats)
        self.__validate_embeddings(stats)
        self.__validate_elastic_documents(stats)
        self.__validate_text_statistics(stats)

    @staticmethod
    def __validate_character_detections(stats: EpisodeStats) -> None:
        detections_file = PathService(stats.series_name).get_episode_file_path(
            stats.episode_info, settings.output_subdirs.character_detections,
        )
        if detections_file.exists():
            result = FileValidator.validate_json_file(detections_file)
            if not result.is_valid:
                stats.errors.append(f'Invalid character detections JSON: {result.error_message}')

    @staticmethod
    def __validate_embeddings(stats: EpisodeStats) -> None:
        embeddings_file = PathService(stats.series_name).get_episode_file_path(
            stats.episode_info, f'{settings.output_subdirs.embeddings}/episode_names',
        )
        if embeddings_file.exists():
            result = FileValidator.validate_json_file(embeddings_file)
            if not result.is_valid:
                stats.errors.append(f'Invalid episode embeddings JSON: {result.error_message}')

    def __validate_elastic_documents(self, stats: EpisodeStats) -> None:
        subdirs_to_check = [
            ELASTIC_SUBDIRS.text_segments, ELASTIC_SUBDIRS.text_embeddings,
            ELASTIC_SUBDIRS.video_frames, ELASTIC_SUBDIRS.episode_names,
            ELASTIC_SUBDIRS.text_statistics, ELASTIC_SUBDIRS.full_episode_embeddings,
            ELASTIC_SUBDIRS.sound_events, ELASTIC_SUBDIRS.sound_event_embeddings,
        ]

        found_any = False
        elastic_base = settings.output_subdirs.elastic_documents
        ep_code = stats.episode_info.episode_code()
        season_code = stats.episode_info.season_code()

        for subdir in subdirs_to_check:
            season_dir = (
                get_base_output_dir(stats.series_name) / elastic_base / subdir / season_code
            )
            if not season_dir.exists():
                continue
            ep_files = list(season_dir.glob(f'{ep_code}_*.jsonl'))
            if not ep_files:
                continue
            found_any = True
            for jsonl_file in ep_files:
                self.__validate_jsonl_file(stats, jsonl_file, subdir)

        if not found_any:
            self._add_warning(stats, f'Missing {settings.output_subdirs.elastic_documents} directory')

    def __validate_jsonl_file(self, stats: EpisodeStats, jsonl_file: Path, subdir: str) -> None:
        result = FileValidator.validate_jsonl_file(jsonl_file)
        if not result.is_valid:
            self._add_error(stats, f'Invalid JSONL {jsonl_file.name}: {result.error_message}')
        else:
            self.__validate_embedding_dimensions(stats, jsonl_file, subdir)

    @staticmethod
    def __validate_text_statistics(stats: EpisodeStats) -> None:
        text_stats_file = PathService(stats.series_name).get_episode_file_path(
            stats.episode_info, 'text_analysis',
        )
        if text_stats_file.exists():
            result = FileValidator.validate_json_file(text_stats_file)
            if not result.is_valid:
                stats.errors.append(f'Invalid text_stats JSON: {result.error_message}')
        else:
            stats.warnings.append(f'Missing text statistics file: {text_stats_file.name}')

    def __validate_embedding_dimensions(self, stats: EpisodeStats, jsonl_file: Path, subdir: str) -> None:
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
        self, stats: EpisodeStats, doc: Dict[str, Any], field: str, expected: int, fname: str,
        lnum: int,
    ) -> None:
        if field in doc and isinstance(doc[field], list):
            actual = len(doc[field])
            if actual != expected:
                self._add_error(stats, f'{fname} line {lnum}: {field} has {actual} dim, expected {expected}')

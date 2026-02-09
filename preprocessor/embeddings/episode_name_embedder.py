import json
import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
    Optional,
)

import numpy as np

from preprocessor.config.config import settings
from preprocessor.core.path_manager import PathManager
from preprocessor.episodes import (
    EpisodeInfo,
    EpisodeManager,
)
from preprocessor.utils.console import console
from preprocessor.utils.constants import EmbeddingKeys
from preprocessor.utils.file_utils import atomic_write_json


class EpisodeNameEmbedder:
    def __init__(
        self,
        model,
        episode_manager: EpisodeManager,
        series_name: str,
        output_dir: Optional[Path] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.model = model
        self.episode_manager = episode_manager
        self.series_name = series_name
        self.output_dir = output_dir or settings.embedding.get_output_dir(series_name)
        self.logger = logger or logging.getLogger(__name__)

    def __generate_episode_name_embeddings(
        self,
        transcription_data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        episode_info_dict = transcription_data.get("episode_info", {})
        season = episode_info_dict.get("season")
        episode_number = episode_info_dict.get("episode_number")

        if season is None or episode_number is None:
            self.logger.warning(
                f"Missing season or episode_number in transcription data: episode_info={episode_info_dict}",
            )
            return None

        episode_info = self.episode_manager.get_episode_by_season_and_relative(
            season,
            episode_number,
        )
        if not episode_info:
            self.logger.warning(f"Cannot find episode info for S{season:02d}E{episode_number:02d}")
            return None

        metadata = self.episode_manager.get_metadata(episode_info)
        title = metadata.get("title")

        if not title:
            self.logger.warning(f"No title found for {episode_info.episode_code()}")
            return None

        embedding = self.__generate_title_embedding(title)
        if embedding is None:
            return None

        episode_id = episode_info.episode_code()

        result = {
            EmbeddingKeys.EPISODE_ID: episode_id,
            EmbeddingKeys.TITLE: title,
            EmbeddingKeys.TITLE_EMBEDDING: embedding.tolist(),
            EmbeddingKeys.EPISODE_METADATA: {
                "season": season,
                "episode_number": episode_number,
                "title": title,
                "premiere_date": metadata.get("premiere_date"),
                "series_name": self.series_name,
                "viewership": metadata.get("viewership"),
            },
        }

        return result

    def __generate_title_embedding(self, title: str) -> Optional[np.ndarray]:
        try:
            embeddings_tensor = self.model.get_text_embeddings(texts=[title])
            embedding = embeddings_tensor[0].cpu().numpy()
            del embeddings_tensor
            return embedding
        except Exception as e:
            self.logger.error(f"Failed to generate embedding for title '{title}': {e}")
            return None

    @staticmethod
    def __save_episode_name_embedding(
        season: int,
        episode: int,
        embedding_data: Dict[str, Any],
        series_name: str,
    ) -> Path:
        path_manager = PathManager(series_name)
        episode_info = EpisodeInfo.create_minimal(season, episode, series_name)

        output_file = path_manager.build_path(
            episode_info,
            settings.output_subdirs.embeddings,
            "episode_name_embedding.json",
        )

        atomic_write_json(output_file, embedding_data, indent=2, ensure_ascii=False)

        return output_file

    def generate_and_save_for_transcription(
        self,
        transcription_data: Dict[str, Any],
    ) -> Optional[Path]:
        embedding_data = self.__generate_episode_name_embeddings(transcription_data)
        if not embedding_data:
            return None

        season = embedding_data[EmbeddingKeys.EPISODE_METADATA]["season"]
        episode = embedding_data[EmbeddingKeys.EPISODE_METADATA]["episode_number"]

        output_file = self.__save_episode_name_embedding(season, episode, embedding_data, self.series_name)
        console.print(
            f"[green]Generated episode name embedding for {embedding_data[EmbeddingKeys.EPISODE_ID]}: {embedding_data[EmbeddingKeys.TITLE]}[/green]",
        )

        return output_file

    @staticmethod
    def load_episode_name_embedding(
        season: int,
        episode: int,
        series_name: str,
        output_dir: Optional[Path] = None,
    ) -> Optional[Dict[str, Any]]:
        if output_dir is None:
            output_dir = settings.embedding.get_output_dir(series_name)

        path_manager = PathManager(series_name)
        episode_info = EpisodeInfo(
            absolute_episode=0,
            season=season,
            relative_episode=episode,
            title="",
            series_name=series_name,
        )

        embedding_file = path_manager.build_path(
            episode_info,
            settings.output_subdirs.embeddings,
            "episode_name_embedding.json",
        )

        if not embedding_file.exists():
            return None

        with open(embedding_file, "r", encoding="utf-8") as f:
            return json.load(f)

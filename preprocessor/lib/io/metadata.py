from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from preprocessor.core.artifacts import EmbeddingCollection


class MetadataBuilder:

    @staticmethod
    def __create_minimal_episode_info(episode_info) -> Dict[str, Any]:
        return {'season': episode_info.season, 'episode_number': episode_info.relative_episode}

    @staticmethod
    def create_processing_metadata(
        episode_info,
        processing_params: Dict[str, Any],
        statistics: Dict[str, Any],
        results_key: str,
        results_data: List[Any],
    ) -> Dict[str, Any]:
        return {
            'generated_at': datetime.now().isoformat(),
            'episode_info': MetadataBuilder.__create_minimal_episode_info(episode_info),
            'processing_parameters': processing_params,
            'statistics': statistics,
            results_key: results_data,
        }

    @staticmethod
    def create_embedding_collection(
        episode_id: str,
        episode_info: Any,
        path: Path,
        model_name: str,
        embedding_count: int,
        embedding_type: str,
    ) -> EmbeddingCollection:
        return EmbeddingCollection(
            episode_id=episode_id,
            episode_info=episode_info,
            path=path,
            model_name=model_name,
            embedding_count=embedding_count,
            embedding_type=embedding_type,
        )

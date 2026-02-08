from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
)


def create_minimal_episode_info(episode_info) -> Dict[str, Any]:
    return {
        "season": episode_info.season,
        "episode_number": episode_info.relative_episode,
    }


def create_processing_metadata(
    episode_info,
    processing_params: Dict[str, Any],
    statistics: Dict[str, Any],
    results_key: str,
    results_data: List[Any],
) -> Dict[str, Any]:
    return {
        "generated_at": datetime.now().isoformat(),
        "episode_info": create_minimal_episode_info(episode_info),
        "processing_parameters": processing_params,
        "statistics": statistics,
        results_key: results_data,
    }

from __future__ import annotations

from pathlib import Path
from typing import (
    List,
    TypeVar,
)

from pydantic import BaseModel

from preprocessor.core.artifacts import (
    EpisodeArtifact,
    TranscriptionData,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.core.output_descriptors import JsonFileOutput

EpisodeInputT = TypeVar('EpisodeInputT', bound=EpisodeArtifact)
ConfigT = TypeVar('ConfigT', bound=BaseModel)


class BaseTranscriptionStep(PipelineStep[EpisodeInputT, TranscriptionData, ConfigT]):
    def get_output_descriptors(self) -> List[JsonFileOutput]:
        return [
            JsonFileOutput(
                pattern='{season}/{episode_num}/{episode}.json',
                subdir='transcriptions/raw',
                min_size_bytes=50,
            ),
        ]

    def _get_cache_path(
            self, input_data: EpisodeInputT, context: ExecutionContext,
    ) -> Path:
        return self._resolve_output_path(
            0,
            context,
            {
                'season': input_data.episode_info.season_code(),
                'episode_num': input_data.episode_info.episode_num(),
                'episode': input_data.episode_info.episode_code(),
            },
        )

from dataclasses import (
    dataclass,
    field,
)
from typing import (
    Any,
    Dict,
    List,
    Optional,
    TypedDict,
)

from preprocessor.services.episodes import EpisodeInfo
from preprocessor.services.validation.base_result import ValidationStatusMixin
from preprocessor.services.validation.validators import (
    CharacterValidator,
    ElasticValidator,
    FaceClusterValidator,
    FrameValidator,
    ImageHashValidator,
    ObjectValidator,
    SceneValidator,
    TranscriptionValidator,
    VideoValidator,
)


class EpisodeStatsData(TypedDict, total=False):
    transcription_chars: Optional[int]
    transcription_duration: Optional[float]
    transcription_words: Optional[int]
    exported_frames_count: Optional[int]
    exported_frames_total_size_mb: Optional[float]
    video_size_mb: Optional[float]
    video_duration: Optional[float]
    scenes_count: Optional[int]


@dataclass
class EpisodeStats(ValidationStatusMixin):
    episode_info: EpisodeInfo
    series_name: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Metryki
    transcription_chars: Optional[int] = None
    transcription_duration: Optional[float] = None
    transcription_words: Optional[int] = None
    exported_frames_count: Optional[int] = None
    exported_frames_total_size_mb: Optional[float] = None
    video_duration: Optional[float] = None
    video_size_mb: Optional[float] = None
    scenes_count: Optional[int] = None

    def __post_init__(self) -> None:
        self.__validators = [
            TranscriptionValidator(), FrameValidator(), VideoValidator(),
            SceneValidator(), ImageHashValidator(), CharacterValidator(),
            FaceClusterValidator(), ObjectValidator(), ElasticValidator(),
        ]

    def collect_stats(self) -> None:
        for v in self.__validators:
            v.validate(self)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status,
            'errors': self.errors,
            'warnings': self.warnings,
            'stats': self.__get_metric_map(),
        }

    def __get_metric_map(self) -> Dict[str, Any]:
        return {
            'transcription_chars': self.transcription_chars,
            'transcription_duration': self.transcription_duration,
            'exported_frames_count': self.exported_frames_count,
            'video_duration': self.video_duration,
            'video_size_mb': self.video_size_mb,
            'scenes_count': self.scenes_count,
        }

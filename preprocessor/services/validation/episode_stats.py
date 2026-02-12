from dataclasses import (
    dataclass,
    field,
)
from typing import (
    List,
    Optional,
    Tuple,
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
from preprocessor.services.validation.validators.base_validator import BaseValidator


class EpisodeStatsData(TypedDict, total=False):
    """Type-safe dict for episode statistics data."""
    transcription_chars: Optional[int]
    transcription_duration: Optional[float]
    transcription_words: Optional[int]
    exported_frames_count: Optional[int]
    exported_frames_total_size_mb: Optional[float]
    exported_frames_avg_resolution: Optional[Tuple[int, int]]
    video_size_mb: Optional[float]
    video_duration: Optional[float]
    video_codec: Optional[str]
    video_resolution: Optional[Tuple[int, int]]
    scenes_count: Optional[int]
    scenes_avg_duration: Optional[float]
    image_hashes_count: Optional[int]
    character_visualizations_count: Optional[int]
    face_clusters_count: Optional[int]
    face_clusters_total_faces: Optional[int]
    object_detections_count: Optional[int]
    object_visualizations_count: Optional[int]


class EpisodeStatsDict(TypedDict):
    """Type-safe dict representation of EpisodeStats."""
    status: str
    errors: List[str]
    warnings: List[str]
    stats: EpisodeStatsData


@dataclass
class EpisodeStats(ValidationStatusMixin):  # pylint: disable=too-many-instance-attributes
    episode_info: EpisodeInfo
    series_name: str
    character_visualizations_count: Optional[int] = None
    errors: List[str] = field(default_factory=list)
    exported_frames_avg_resolution: Optional[Tuple[int, int]] = None
    exported_frames_count: Optional[int] = None
    exported_frames_total_size_mb: Optional[float] = None
    face_clusters_count: Optional[int] = None
    face_clusters_total_faces: Optional[int] = None
    image_hashes_count: Optional[int] = None
    object_detections_count: Optional[int] = None
    object_visualizations_count: Optional[int] = None
    scenes_avg_duration: Optional[float] = None
    scenes_count: Optional[int] = None
    transcription_chars: Optional[int] = None
    transcription_duration: Optional[float] = None
    transcription_words: Optional[int] = None
    video_codec: Optional[str] = None
    video_duration: Optional[float] = None
    video_resolution: Optional[Tuple[int, int]] = None
    video_size_mb: Optional[float] = None
    warnings: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._validators: List[BaseValidator] = [
            TranscriptionValidator(),
            FrameValidator(),
            VideoValidator(),
            SceneValidator(),
            ImageHashValidator(),
            CharacterValidator(),
            FaceClusterValidator(),
            ObjectValidator(),
            ElasticValidator(),
        ]

    def collect_stats(self) -> None:
        for validator in self._validators:
            validator.validate(self)

    def to_dict(self) -> EpisodeStatsDict:
        return {
            'status': self.status,
            'errors': self.errors,
            'warnings': self.warnings,
            'stats': {
                'transcription_chars': self.transcription_chars,
                'transcription_duration': self.transcription_duration,
                'transcription_words': self.transcription_words,
                'exported_frames_count': self.exported_frames_count,
                'exported_frames_total_size_mb': self.exported_frames_total_size_mb,
                'exported_frames_avg_resolution': self.exported_frames_avg_resolution,
                'video_size_mb': self.video_size_mb,
                'video_duration': self.video_duration,
                'video_codec': self.video_codec,
                'video_resolution': self.video_resolution,
                'scenes_count': self.scenes_count,
                'scenes_avg_duration': self.scenes_avg_duration,
                'image_hashes_count': self.image_hashes_count,
                'character_visualizations_count': self.character_visualizations_count,
                'face_clusters_count': self.face_clusters_count,
                'face_clusters_total_faces': self.face_clusters_total_faces,
                'object_detections_count': self.object_detections_count,
                'object_visualizations_count': self.object_visualizations_count,
            },
        }

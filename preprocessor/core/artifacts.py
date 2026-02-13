from dataclasses import (
    dataclass,
    field,
)
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
)

if TYPE_CHECKING:
    from preprocessor.services.episodes.episode_manager import EpisodeInfo


@dataclass(frozen=True)
class Artifact:
    pass


@dataclass(frozen=True)
class EpisodeArtifact(Artifact):
    episode_id: str
    episode_info: 'EpisodeInfo'


@dataclass(frozen=True)
class SourceVideo(EpisodeArtifact):
    path: Path


@dataclass(frozen=True)
class TranscodedVideo(EpisodeArtifact):
    codec: str
    path: Path
    resolution: str


@dataclass(frozen=True)
class SceneCollection(EpisodeArtifact):
    min_scene_len: int
    path: Path
    scenes: List[Dict[str, Any]]
    threshold: float
    video_path: Path


@dataclass(frozen=True)
class FrameCollection(EpisodeArtifact):
    directory: Path
    frame_count: int
    metadata_path: Path


@dataclass(frozen=True)
class TranscriptionData(EpisodeArtifact):
    format: str
    language: str
    model: str
    path: Path


@dataclass(frozen=True)
class EmbeddingCollection(EpisodeArtifact):
    embedding_count: int
    embedding_type: str
    model_name: str
    path: Path


@dataclass(frozen=True)
class DetectionResults(EpisodeArtifact):
    detection_count: int
    detection_type: str
    path: Path


@dataclass(frozen=True)
class ElasticDocuments(EpisodeArtifact):
    document_count: int
    path: Path


@dataclass(frozen=True)
class TextAnalysisResults(EpisodeArtifact):
    path: Path
    statistics: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = field(default=None)


@dataclass(frozen=True)
class AudioArtifact(EpisodeArtifact):
    format: str
    path: Path


@dataclass(frozen=True)
class IndexingResult(Artifact):
    document_count: int
    index_name: str
    success: bool


@dataclass(frozen=True)
class ImageHashCollection(EpisodeArtifact):
    hash_count: int
    path: Path


@dataclass(frozen=True)
class EmotionData(EpisodeArtifact):
    path: Path


@dataclass(frozen=True)
class ClusterData(EpisodeArtifact):
    path: Path


@dataclass(frozen=True)
class ObjectDetectionData(EpisodeArtifact):
    path: Path


@dataclass(frozen=True)
class ArchiveArtifact(EpisodeArtifact):
    path: Path


@dataclass(frozen=True)
class ValidationResult(Artifact):
    season: str
    validation_report_dir: Path


@dataclass(frozen=True)
class ResolutionAnalysisResult(Artifact):
    total_files: int
    upscaling_percentage: float


ProcessedEpisode = ElasticDocuments

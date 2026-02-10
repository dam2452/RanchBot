from dataclasses import (
    dataclass,
    field,
)
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)


@dataclass(frozen=True)
class Artifact:
    pass

@dataclass(frozen=True)
class EpisodeArtifact(Artifact):
    episode_id: str
    episode_info: Any

@dataclass(frozen=True)
class SourceVideo(EpisodeArtifact):
    path: Path

@dataclass(frozen=True)
class TranscodedVideo(EpisodeArtifact):
    path: Path
    resolution: str
    codec: str

@dataclass(frozen=True)
class SceneCollection(EpisodeArtifact):
    path: Path
    video_path: Path
    scenes: List[Dict[str, Any]]
    threshold: float
    min_scene_len: int

@dataclass(frozen=True)
class FrameCollection(EpisodeArtifact):
    directory: Path
    frame_count: int
    metadata_path: Path

@dataclass(frozen=True)
class TranscriptionData(EpisodeArtifact):
    path: Path
    language: str
    model: str
    format: str

@dataclass(frozen=True)
class EmbeddingCollection(EpisodeArtifact):
    path: Path
    model_name: str
    embedding_count: int
    embedding_type: str

@dataclass(frozen=True)
class DetectionResults(EpisodeArtifact):
    path: Path
    detection_type: str
    detection_count: int

@dataclass(frozen=True)
class ElasticDocuments(EpisodeArtifact):
    path: Path
    document_count: int

@dataclass(frozen=True)
class TextAnalysisResults(EpisodeArtifact):
    path: Path
    statistics: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = field(default=None)

@dataclass(frozen=True)
class AudioArtifact(EpisodeArtifact):
    path: Path
    format: str

@dataclass(frozen=True)
class IndexingResult(Artifact):
    index_name: str
    document_count: int
    success: bool

@dataclass(frozen=True)
class ImageHashCollection(EpisodeArtifact):
    path: Path
    hash_count: int

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

ProcessedEpisode = ElasticDocuments

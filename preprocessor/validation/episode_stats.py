import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from preprocessor.config.config import settings
from preprocessor.core.constants import OUTPUT_FILE_NAMES, OUTPUT_FILE_PATTERNS
from preprocessor.core.episode_manager import EpisodeInfo
from preprocessor.validation.file_validators import (
    ValidationResult,
    validate_image_file,
    validate_json_file,
    validate_jsonl_file,
    validate_video_file,
)


@dataclass
class EpisodeStats:
    episode_info: EpisodeInfo
    episode_path: Path
    series_name: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    transcription_chars: Optional[int] = None
    transcription_duration: Optional[float] = None
    transcription_words: Optional[int] = None

    exported_frames_count: Optional[int] = None
    exported_frames_total_size_mb: Optional[float] = None
    exported_frames_avg_resolution: Optional[tuple] = None

    video_size_mb: Optional[float] = None
    video_duration: Optional[float] = None
    video_codec: Optional[str] = None
    video_resolution: Optional[tuple] = None

    scenes_count: Optional[int] = None
    scenes_avg_duration: Optional[float] = None

    def collect_stats(self):
        self._validate_transcription()
        self._validate_exported_frames()
        self._validate_video()
        self._validate_scenes()
        self._validate_other_files()

    def _validate_transcription(self):
        transcriptions_dir = self.episode_path / settings.output_subdirs.transcriptions
        transcription_file = transcriptions_dir / f"{self.series_name}_{self.episode_info.episode_code()}.json"
        if not transcription_file.exists():
            self.errors.append(f"Missing transcription file: {transcription_file}")
            return

        result = validate_json_file(transcription_file)
        if not result.is_valid:
            self.errors.append(f"Invalid transcription JSON: {result.error_message}")
            return

        try:
            with open(transcription_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            text = data.get("text", "")
            self.transcription_chars = len(text)
            self.transcription_words = len(text.split())

            words = data.get("words", [])
            if words:
                last_word = words[-1]
                self.transcription_duration = last_word.get("end", 0.0)
        except Exception as e:
            self.errors.append(f"Error reading transcription: {e}")

    def _validate_exported_frames(self):
        frames_dir = self.episode_path / settings.output_subdirs.frames
        if not frames_dir.exists():
            self.errors.append(f"Missing {settings.output_subdirs.frames} directory: {frames_dir}")
            return

        frame_files = sorted(frames_dir.glob(OUTPUT_FILE_PATTERNS["frame"]))
        if not frame_files:
            self.errors.append(f"No frames found in {settings.output_subdirs.frames}/")
            return

        self.exported_frames_count = len(frame_files)

        total_size = 0
        resolutions = []
        invalid_count = 0

        for frame_file in frame_files:
            result = validate_image_file(frame_file)
            if result.is_valid:
                total_size += result.metadata["size_mb"]
                resolutions.append((result.metadata["width"], result.metadata["height"]))
            else:
                invalid_count += 1
                self.errors.append(f"Invalid frame {frame_file.name}: {result.error_message}")

        if invalid_count > 0:
            self.warnings.append(f"{invalid_count} invalid frames found")

        self.exported_frames_total_size_mb = round(total_size, 2)

        if resolutions:
            most_common_res = max(set(resolutions), key=resolutions.count)
            self.exported_frames_avg_resolution = most_common_res

    def _validate_video(self):
        videos_dir = self.episode_path / settings.output_subdirs.video
        video_file = videos_dir / f"{self.series_name}_{self.episode_info.episode_code()}.mp4"
        if not video_file.exists():
            self.errors.append(f"Missing video file: {video_file}")
            return

        result = validate_video_file(video_file)
        if not result.is_valid:
            self.errors.append(f"Invalid video: {result.error_message}")
            return

        self.video_size_mb = result.metadata["size_mb"]
        self.video_duration = result.metadata["duration"]
        self.video_codec = result.metadata["codec"]
        self.video_resolution = (result.metadata["width"], result.metadata["height"])

    def _validate_scenes(self):
        scenes_dir = self.episode_path / settings.output_subdirs.scenes
        scenes_file = scenes_dir / f"{self.series_name}_{self.episode_info.episode_code()}{OUTPUT_FILE_PATTERNS['scenes_suffix']}"
        if not scenes_file.exists():
            self.errors.append(f"Missing scenes file: {scenes_file}")
            return

        result = validate_json_file(scenes_file)
        if not result.is_valid:
            self.errors.append(f"Invalid scenes JSON: {result.error_message}")
            return

        try:
            with open(scenes_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.scenes_count = data.get("total_scenes", 0)
            scenes = data.get("scenes", [])
            if scenes:
                durations = [scene.get("duration", 0) for scene in scenes]
                self.scenes_avg_duration = round(sum(durations) / len(durations), 2)
        except Exception as e:
            self.errors.append(f"Error reading scenes: {e}")

    def _validate_other_files(self):
        detections_file = self.episode_path / OUTPUT_FILE_NAMES["detections"]
        if detections_file.exists():
            result = validate_json_file(detections_file)
            if not result.is_valid:
                self.errors.append(f"Invalid {OUTPUT_FILE_NAMES['detections']}: {result.error_message}")

        episode_embedding_file = self.episode_path / OUTPUT_FILE_NAMES["episode_embedding"]
        if episode_embedding_file.exists():
            result = validate_json_file(episode_embedding_file)
            if not result.is_valid:
                self.errors.append(f"Invalid {OUTPUT_FILE_NAMES['episode_embedding']}: {result.error_message}")

        embeddings_dir = self.episode_path / settings.output_subdirs.embeddings
        if embeddings_dir.exists():
            embeddings_file = embeddings_dir / OUTPUT_FILE_NAMES["embeddings_text"]
            if embeddings_file.exists():
                result = validate_json_file(embeddings_file)
                if not result.is_valid:
                    self.errors.append(f"Invalid {OUTPUT_FILE_NAMES['embeddings_text']}: {result.error_message}")

        elastic_docs_dir = self.episode_path / settings.output_subdirs.elastic_documents
        if elastic_docs_dir.exists():
            for jsonl_file in elastic_docs_dir.rglob("*.jsonl"):
                result = validate_jsonl_file(jsonl_file)
                if not result.is_valid:
                    self.errors.append(f"Invalid JSONL {jsonl_file.name}: {result.error_message}")
        else:
            self.warnings.append(f"Missing {settings.output_subdirs.elastic_documents} directory")

        transcriptions_dir = self.episode_path / settings.output_subdirs.transcriptions
        if transcriptions_dir.exists():
            text_stats_file = transcriptions_dir / f"{self.series_name}_{self.episode_info.episode_code()}_text_stats.json"
            if text_stats_file.exists():
                result = validate_json_file(text_stats_file)
                if not result.is_valid:
                    self.errors.append(f"Invalid text_stats JSON: {result.error_message}")
            else:
                self.warnings.append(f"Missing text statistics file: {text_stats_file.name}")

    @property
    def status(self) -> str:
        if self.errors:
            return "FAIL"
        if self.warnings:
            return "WARNING"
        return "PASS"

    def to_dict(self) -> Dict:
        return {
            "status": self.status,
            "errors": self.errors,
            "warnings": self.warnings,
            "stats": {
                "transcription_chars": self.transcription_chars,
                "transcription_duration": self.transcription_duration,
                "transcription_words": self.transcription_words,
                "exported_frames_count": self.exported_frames_count,
                "exported_frames_total_size_mb": self.exported_frames_total_size_mb,
                "exported_frames_avg_resolution": self.exported_frames_avg_resolution,
                "video_size_mb": self.video_size_mb,
                "video_duration": self.video_duration,
                "video_codec": self.video_codec,
                "video_resolution": self.video_resolution,
                "scenes_count": self.scenes_count,
                "scenes_avg_duration": self.scenes_avg_duration,
            },
        }

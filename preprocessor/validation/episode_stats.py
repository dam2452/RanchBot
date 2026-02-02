from dataclasses import (
    dataclass,
    field,
)
import json
from typing import (
    Dict,
    List,
    Optional,
)

from preprocessor.config.config import settings
from preprocessor.core.constants import (
    OUTPUT_FILE_NAMES,
    OUTPUT_FILE_PATTERNS,
)
from preprocessor.core.episode_manager import (
    EpisodeInfo,
    EpisodeManager,
)
from preprocessor.core.output_path_builder import OutputPathBuilder
from preprocessor.validation.base_result import ValidationStatusMixin
from preprocessor.validation.file_validators import (
    validate_image_file,
    validate_json_file,
    validate_jsonl_file,
    validate_video_file,
)

ELASTIC_SUBDIRS = settings.output_subdirs.elastic_document_subdirs


@dataclass
class EpisodeStats(ValidationStatusMixin):  # pylint: disable=too-many-instance-attributes
    episode_info: EpisodeInfo
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

    image_hashes_count: Optional[int] = None
    object_detections_count: Optional[int] = None
    object_visualizations_count: Optional[int] = None
    character_visualizations_count: Optional[int] = None
    face_clusters_count: Optional[int] = None
    face_clusters_total_faces: Optional[int] = None

    def collect_stats(self):
        self.__validate_transcription()
        self.__validate_exported_frames()
        self.__validate_video()
        self.__validate_scenes()
        self.__validate_image_hashes()
        self.__validate_character_visualizations()
        self.__validate_face_clusters()
        self.__validate_object_detections()
        self.__validate_object_visualizations()
        self.__validate_other_files()

    def __validate_transcription(self):
        transcriptions_dir = EpisodeManager.get_episode_subdir(self.episode_info, settings.output_subdirs.transcriptions)
        base_name = f"{self.series_name}_{self.episode_info.episode_code()}"

        raw_dir = transcriptions_dir / settings.output_subdirs.transcription_subdirs.raw
        clean_dir = transcriptions_dir / settings.output_subdirs.transcription_subdirs.clean
        sound_events_dir = transcriptions_dir / settings.output_subdirs.transcription_subdirs.sound_events

        transcription_files = {
            "main": raw_dir / f"{base_name}.json",
            "segmented": raw_dir / f"{base_name}_segmented.json",
            "simple": raw_dir / f"{base_name}_simple.json",
            "clean": clean_dir / f"{base_name}_clean_transcription.json",
            "clean_txt": clean_dir / f"{base_name}_clean_transcription.txt",
            "sound_events": sound_events_dir / f"{base_name}_sound_events.json",
        }

        if not any(f.exists() for f in transcription_files.values()):
            self.errors.append("No transcription files found in any format")
            return

        self.__validate_raw_transcription(transcription_files)
        self.__validate_clean_transcription(transcription_files["clean"])
        self.__validate_clean_txt(transcription_files["clean_txt"])
        self.__validate_sound_events(transcription_files["sound_events"])

    def __validate_raw_transcription(self, transcription_files: Dict):
        raw_transcription = None
        for key in ("main", "segmented", "simple"):
            if transcription_files[key].exists():
                raw_transcription = transcription_files[key]
                break

        if not raw_transcription:
            self.warnings.append("Missing raw transcription file (checked: .json, _segmented.json, _simple.json)")
            return

        result = validate_json_file(raw_transcription)
        if not result.is_valid:
            self.errors.append(f"Invalid transcription JSON: {result.error_message}")
            return

        self.__extract_transcription_stats(raw_transcription)

    def __extract_transcription_stats(self, raw_transcription):
        try:
            with open(raw_transcription, "r", encoding="utf-8") as f:
                data = json.load(f)

            text = data.get("text", "")
            if not text:
                segments = data.get("segments", [])
                if segments:
                    text = " ".join(seg.get("text", "") for seg in segments)

            self.transcription_chars = len(text)
            self.transcription_words = len(text.split())

            words = data.get("words", [])
            if words:
                self.transcription_duration = words[-1].get("end", 0.0)
            else:
                segments = data.get("segments", [])
                if segments and segments[-1].get("end"):
                    self.transcription_duration = segments[-1].get("end", 0.0)
        except Exception as e:
            self.errors.append(f"Error reading transcription: {e}")

    def __validate_clean_transcription(self, clean_transcription_file):
        if not clean_transcription_file.exists():
            self.warnings.append(f"Missing clean transcription file: {clean_transcription_file.name}")
            return

        result = validate_json_file(clean_transcription_file)
        if not result.is_valid:
            self.warnings.append(f"Invalid clean transcription JSON: {result.error_message}")

    def __validate_clean_txt(self, clean_txt_file):
        if not clean_txt_file.exists():
            self.warnings.append(f"Missing clean transcription txt: {clean_txt_file.name}")

    def __validate_sound_events(self, sound_events_file):
        if not sound_events_file.exists():
            self.warnings.append(f"Missing sound events file: {sound_events_file.name}")
            return

        result = validate_json_file(sound_events_file)
        if not result.is_valid:
            self.warnings.append(f"Invalid sound events JSON: {result.error_message}")

    def __validate_exported_frames(self):
        frames_dir = EpisodeManager.get_episode_subdir(self.episode_info, settings.output_subdirs.frames)
        if not frames_dir.exists():
            self.warnings.append(f"Missing {settings.output_subdirs.frames} directory: {frames_dir}")
            return

        frame_files = sorted(frames_dir.glob(OUTPUT_FILE_PATTERNS["frame"]))
        if not frame_files:
            self.warnings.append(f"No frames found in {settings.output_subdirs.frames}/")
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

    def __validate_video(self):
        video_file = OutputPathBuilder.build_video_path(self.episode_info, self.series_name)
        if not video_file.exists():
            self.warnings.append(f"Missing video file: {video_file}")
            return

        result = validate_video_file(video_file)
        if not result.is_valid:
            self.errors.append(f"Invalid video: {result.error_message}")
            return

        self.video_size_mb = result.metadata["size_mb"]
        self.video_duration = result.metadata["duration"]
        self.video_codec = result.metadata["codec"]
        self.video_resolution = (result.metadata["width"], result.metadata["height"])

    def __validate_scenes(self):
        scenes_dir = EpisodeManager.get_episode_subdir(self.episode_info, settings.output_subdirs.scenes)
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

    def __validate_image_hashes(self):
        hashes_dir = EpisodeManager.get_episode_subdir(self.episode_info, settings.output_subdirs.image_hashes)
        if not hashes_dir.exists():
            self.warnings.append(f"Missing {settings.output_subdirs.image_hashes} directory")
            return

        json_files = list(hashes_dir.glob("*.json"))
        if not json_files:
            self.warnings.append(f"No JSON files in {settings.output_subdirs.image_hashes}/")
            return

        self.image_hashes_count = len(json_files)
        sizes = []

        for json_file in json_files:
            result = validate_json_file(json_file)
            if not result.is_valid:
                self.errors.append(f"Invalid image hash JSON {json_file.name}: {result.error_message}")
            else:
                sizes.append(json_file.stat().st_size)

        self.__check_size_anomalies(sizes, "image_hashes")

    def __validate_character_visualizations(self):
        viz_dir = EpisodeManager.get_episode_subdir(self.episode_info, settings.output_subdirs.character_visualizations)
        if not viz_dir.exists():
            return

        image_files = list(viz_dir.glob("*.jpg")) + list(viz_dir.glob("*.png"))
        if not image_files:
            self.warnings.append(f"No visualization images in {settings.output_subdirs.character_visualizations}/")
            return

        self.character_visualizations_count = len(image_files)
        invalid_count = 0

        for img_file in image_files:
            result = validate_image_file(img_file)
            if not result.is_valid:
                invalid_count += 1
                self.errors.append(f"Invalid character visualization {img_file.name}: {result.error_message}")

        if invalid_count > 0:
            self.warnings.append(f"{invalid_count} invalid character visualization images found")

    def __validate_face_clusters(self):
        clusters_dir = EpisodeManager.get_episode_subdir(self.episode_info, settings.output_subdirs.face_clusters)
        if not clusters_dir.exists():
            return

        metadata_files = list(clusters_dir.glob("*_face_clusters.json"))
        metadata_file = metadata_files[0] if metadata_files else None

        if not metadata_file or not metadata_file.exists():
            self.warnings.append("Missing face clustering metadata file")
            return

        result = validate_json_file(metadata_file)
        if not result.is_valid:
            self.errors.append(f"Invalid face clustering metadata: {result.error_message}")
            return

        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            clusters = data.get("clusters", {})

            if isinstance(clusters, dict):
                self.face_clusters_count = len(clusters)
                total_faces = 0
                for _, cluster_info in clusters.items():
                    total_faces += cluster_info.get("face_count", 0)
            elif isinstance(clusters, list):
                self.face_clusters_count = len(clusters)
                total_faces = 0
                for cluster_info in clusters:
                    total_faces += cluster_info.get("face_count", 0)
            else:
                self.warnings.append("Unexpected clusters format in face clustering metadata")
                return

            noise_info = data.get("noise", {})
            if noise_info:
                total_faces += noise_info.get("face_count", 0)

            self.face_clusters_total_faces = total_faces

        except Exception as e:
            self.errors.append(f"Error reading face clustering metadata: {e}")

    def __validate_object_detections(self):
        detections_dir = EpisodeManager.get_episode_subdir(self.episode_info, settings.output_subdirs.object_detections)
        if not detections_dir.exists():
            self.warnings.append(f"Missing {settings.output_subdirs.object_detections} directory")
            return

        json_files = [f for f in detections_dir.glob("*.json") if "visualizations" not in str(f)]
        if not json_files:
            self.warnings.append(f"No JSON files in {settings.output_subdirs.object_detections}/")
            return

        self.object_detections_count = len(json_files)
        sizes = []

        for json_file in json_files:
            result = validate_json_file(json_file)
            if not result.is_valid:
                self.errors.append(f"Invalid object detection JSON {json_file.name}: {result.error_message}")
            else:
                sizes.append(json_file.stat().st_size)

        self.__check_size_anomalies(sizes, "object_detections")

    def __validate_object_visualizations(self):
        viz_dir = EpisodeManager.get_episode_subdir(self.episode_info, settings.output_subdirs.object_visualizations)
        if not viz_dir.exists():
            return

        image_files = list(viz_dir.glob("*.jpg")) + list(viz_dir.glob("*.png"))
        if not image_files:
            self.warnings.append(f"No visualization images in {settings.output_subdirs.object_visualizations}/")
            return

        self.object_visualizations_count = len(image_files)
        invalid_count = 0

        for img_file in image_files:
            result = validate_image_file(img_file)
            if not result.is_valid:
                invalid_count += 1
                self.errors.append(f"Invalid visualization {img_file.name}: {result.error_message}")

        if invalid_count > 0:
            self.warnings.append(f"{invalid_count} invalid visualization images found")

    def __validate_embedding_dimensions(self, jsonl_file, subdir: str):
        embedding_fields = {
            ELASTIC_SUBDIRS.text_embeddings: "text_embedding",
            ELASTIC_SUBDIRS.video_frames: "video_embedding",
            ELASTIC_SUBDIRS.episode_names: "title_embedding",
            ELASTIC_SUBDIRS.full_episode_embeddings: "full_episode_embedding",
            ELASTIC_SUBDIRS.sound_event_embeddings: "sound_event_embedding",
        }

        if subdir not in embedding_fields:
            return

        embedding_field = embedding_fields[subdir]
        expected_dim = settings.embedding_model.embedding_dim

        try:
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    doc = json.loads(line)
                    if embedding_field in doc:
                        embedding = doc[embedding_field]
                        if isinstance(embedding, list):
                            actual_dim = len(embedding)
                            if actual_dim != expected_dim:
                                self.errors.append(
                                    f"{jsonl_file.name} line {line_num}: "
                                    f"{embedding_field} has {actual_dim} dimensions, expected {expected_dim}",
                                )
                                return
        except Exception as e:
            self.errors.append(f"Error validating embeddings in {jsonl_file.name}: {e}")

    def __check_size_anomalies(self, sizes: List[int], folder_name: str, threshold: float = 0.2):
        if len(sizes) < 2:
            return

        avg_size = sum(sizes) / len(sizes)
        if avg_size == 0:
            return

        for i, size in enumerate(sizes):
            deviation = abs(size - avg_size) / avg_size
            if deviation > threshold:
                self.warnings.append(
                    f"{folder_name} file #{i+1} size deviation: {deviation*100:.1f}% from average",
                )

    def __validate_other_files(self):
        char_detections_dir = EpisodeManager.get_episode_subdir(self.episode_info, settings.output_subdirs.character_detections)
        detections_file = char_detections_dir / OUTPUT_FILE_NAMES["detections"]
        if detections_file.exists():
            result = validate_json_file(detections_file)
            if not result.is_valid:
                self.errors.append(f"Invalid {OUTPUT_FILE_NAMES['detections']}: {result.error_message}")

        embeddings_dir = EpisodeManager.get_episode_subdir(self.episode_info, settings.output_subdirs.embeddings)
        if embeddings_dir.exists():
            embeddings_file = embeddings_dir / OUTPUT_FILE_NAMES["embeddings_text"]
            if embeddings_file.exists():
                result = validate_json_file(embeddings_file)
                if not result.is_valid:
                    self.errors.append(f"Invalid {OUTPUT_FILE_NAMES['embeddings_text']}: {result.error_message}")

        elastic_subdirs = [
            ELASTIC_SUBDIRS.text_segments,
            ELASTIC_SUBDIRS.text_embeddings,
            ELASTIC_SUBDIRS.video_frames,
            ELASTIC_SUBDIRS.episode_names,
            ELASTIC_SUBDIRS.text_statistics,
            ELASTIC_SUBDIRS.full_episode_embeddings,
            ELASTIC_SUBDIRS.sound_events,
            ELASTIC_SUBDIRS.sound_event_embeddings,
        ]
        found_elastic_docs = False
        for subdir in elastic_subdirs:
            elastic_docs_dir = EpisodeManager.get_episode_subdir(
                self.episode_info,
                f"{settings.output_subdirs.elastic_documents}/{subdir}",
            )
            if elastic_docs_dir.exists():
                found_elastic_docs = True
                for jsonl_file in elastic_docs_dir.glob("*.jsonl"):
                    result = validate_jsonl_file(jsonl_file)
                    if not result.is_valid:
                        self.errors.append(f"Invalid JSONL {jsonl_file.name}: {result.error_message}")
                    else:
                        self.__validate_embedding_dimensions(jsonl_file, subdir)

        if not found_elastic_docs:
            self.warnings.append(f"Missing {settings.output_subdirs.elastic_documents} directory")

        transcriptions_dir = EpisodeManager.get_episode_subdir(self.episode_info, settings.output_subdirs.transcriptions)
        if transcriptions_dir.exists():
            clean_dir = transcriptions_dir / settings.output_subdirs.transcription_subdirs.clean
            text_stats_file = clean_dir / f"{self.series_name}_{self.episode_info.episode_code()}_text_stats.json"
            if text_stats_file.exists():
                result = validate_json_file(text_stats_file)
                if not result.is_valid:
                    self.errors.append(f"Invalid text_stats JSON: {result.error_message}")
            else:
                self.warnings.append(f"Missing text statistics file: {text_stats_file.name}")

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
                "image_hashes_count": self.image_hashes_count,
                "character_visualizations_count": self.character_visualizations_count,
                "face_clusters_count": self.face_clusters_count,
                "face_clusters_total_faces": self.face_clusters_total_faces,
                "object_detections_count": self.object_detections_count,
                "object_visualizations_count": self.object_visualizations_count,
            },
        }

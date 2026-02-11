from dataclasses import (
    dataclass,
    field,
)
import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from preprocessor.config.config import (
    get_base_output_dir,
    settings,
)
from preprocessor.config.constants import (
    DEFAULT_VIDEO_EXTENSION,
    OUTPUT_FILE_NAMES,
    OUTPUT_FILE_PATTERNS,
)
from preprocessor.lib.episodes import EpisodeInfo
from preprocessor.lib.io.path_manager import PathManager
from preprocessor.modules.validation.base_result import ValidationStatusMixin
from preprocessor.modules.validation.file_validators import FileValidator

ELASTIC_SUBDIRS = settings.output_subdirs.elastic_document_subdirs

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

    def to_dict(self) -> Dict[str, Any]:
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

    def __check_size_anomalies(
        self, sizes: List[int], folder_name: str, threshold: float = 0.2,
    ):
        if len(sizes) < 2:
            return
        avg_size = sum(sizes) / len(sizes)
        if avg_size == 0:
            return
        for i, size in enumerate(sizes):
            deviation = abs(size - avg_size) / avg_size
            if deviation > threshold:
                warning_msg = (
                    f'{folder_name} file #{i + 1} size deviation: '
                    f'{deviation * 100:.1f}% from average'
                )
                self.warnings.append(warning_msg)

    def __extract_transcription_stats(self, raw_transcription: Path):
        data = self.__load_json_safely(raw_transcription)
        if not data:
            self.errors.append(f'Error reading transcription: {raw_transcription}')
            return
        text = data.get('text', '')
        if not text:
            segments = data.get('segments', [])
            if segments:
                text = ' '.join((seg.get('text', '') for seg in segments))
        self.transcription_chars = len(text)
        self.transcription_words = len(text.split())
        words = data.get('words', [])
        if words:
            self.transcription_duration = words[-1].get('end', 0.0)
        else:
            segments = data.get('segments', [])
            if segments and segments[-1].get('end'):
                self.transcription_duration = segments[-1].get('end', 0.0)

    @staticmethod
    def __load_json_safely(file_path: Path) -> Optional[Dict[str, Any]]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def __validate_character_visualizations(self):
        self.__validate_visualizations(settings.output_subdirs.character_visualizations, 'character_visualizations_count', 'character visualization')

    def __validate_clean_transcription(self, clean_transcription_file):
        if not clean_transcription_file.exists():
            self.warnings.append(f'Missing clean transcription file: {clean_transcription_file.name}')
            return
        result = FileValidator.validate_json_file(clean_transcription_file)
        if not result.is_valid:
            self.warnings.append(f'Invalid clean transcription JSON: {result.error_message}')

    def __validate_clean_txt(self, clean_txt_file):
        if not clean_txt_file.exists():
            self.warnings.append(f'Missing clean transcription txt: {clean_txt_file.name}')

    def __validate_embedding_dimensions(self, jsonl_file, subdir: str):
        embedding_fields = {
            ELASTIC_SUBDIRS.text_embeddings: 'text_embedding',
            ELASTIC_SUBDIRS.video_frames: 'video_embedding',
            ELASTIC_SUBDIRS.episode_names: 'title_embedding',
            ELASTIC_SUBDIRS.full_episode_embeddings: 'full_episode_embedding',
            ELASTIC_SUBDIRS.sound_event_embeddings: 'sound_event_embedding',
        }
        if subdir not in embedding_fields:
            return
        embedding_field = embedding_fields[subdir]
        expected_dim = settings.embedding_model.embedding_dim
        try:
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    doc = json.loads(line)
                    if embedding_field in doc:
                        embedding = doc[embedding_field]
                        if isinstance(embedding, list):
                            actual_dim = len(embedding)
                            if actual_dim != expected_dim:
                                error_msg = (
                                    f'{jsonl_file.name} line {line_num}: '
                                    f'{embedding_field} has {actual_dim} dimensions, '
                                    f'expected {expected_dim}'
                                )
                                self.errors.append(error_msg)
                                return
        except Exception as e:
            self.errors.append(f'Error validating embeddings in {jsonl_file.name}: {e}')

    def __validate_exported_frames(self):
        frames_dir = PathManager(self.series_name).get_episode_dir(self.episode_info, settings.output_subdirs.frames)
        if not frames_dir.exists():
            self.warnings.append(f'Missing {settings.output_subdirs.frames} directory: {frames_dir}')
            return
        frame_files = sorted(frames_dir.glob(OUTPUT_FILE_PATTERNS['frame']))
        if not frame_files:
            self.warnings.append(f'No frames found in {settings.output_subdirs.frames}/')
            return
        self.exported_frames_count = len(frame_files)
        total_size = 0
        resolutions = []
        invalid_count = 0
        for frame_file in frame_files:
            result = FileValidator.validate_image_file(frame_file)
            if result.is_valid:
                total_size += result.metadata['size_mb']
                resolutions.append((result.metadata['width'], result.metadata['height']))
            else:
                invalid_count += 1
                self.errors.append(f'Invalid frame {frame_file.name}: {result.error_message}')
        if invalid_count > 0:
            self.warnings.append(f'{invalid_count} invalid frames found')
        self.exported_frames_total_size_mb = round(total_size, 2)
        if resolutions:
            most_common_res = max(set(resolutions), key=resolutions.count)
            self.exported_frames_avg_resolution = most_common_res

    def __validate_face_clusters(self):
        clusters_dir = PathManager(self.series_name).get_episode_dir(self.episode_info, settings.output_subdirs.face_clusters)
        if not clusters_dir.exists():
            return
        metadata_files = list(clusters_dir.glob('*_face_clusters.json'))
        metadata_file = metadata_files[0] if metadata_files else None
        if not metadata_file or not metadata_file.exists():
            self.warnings.append('Missing face clustering metadata file')
            return
        result = FileValidator.validate_json_file(metadata_file)
        if not result.is_valid:
            self.errors.append(f'Invalid face clustering metadata: {result.error_message}')
            return
        data = self.__load_json_safely(metadata_file)
        if not data:
            self.errors.append(f'Error reading face clustering metadata: {metadata_file}')
            return
        clusters = data.get('clusters', {})
        if isinstance(clusters, dict):
            self.face_clusters_count = len(clusters)
            total_faces = sum((cluster_info.get('face_count', 0) for cluster_info in clusters.values()))
        elif isinstance(clusters, list):
            self.face_clusters_count = len(clusters)
            total_faces = sum((cluster_info.get('face_count', 0) for cluster_info in clusters))
        else:
            self.warnings.append('Unexpected clusters format in face clustering metadata')
            return
        noise_info = data.get('noise', {})
        if noise_info:
            total_faces += noise_info.get('face_count', 0)
        self.face_clusters_total_faces = total_faces

    def __validate_image_hashes(self):
        self.__validate_json_directory(settings.output_subdirs.image_hashes, 'image_hashes_count', 'image_hashes')

    @staticmethod
    def __validate_images_in_directory(
        directory: Path,
        extensions: Tuple[str, ...] = ('*.jpg', '*.png'),
    ) -> Tuple[int, int, List[str]]:
        if not directory.exists():
            return 0, 0, []
        image_files = []
        for ext in extensions:
            image_files.extend(directory.glob(ext))
        if not image_files:
            return 0, 0, []
        invalid_count = 0
        errors = []
        for img_file in image_files:
            result = FileValidator.validate_image_file(img_file)
            if not result.is_valid:
                invalid_count += 1
                errors.append(f'Invalid image {img_file.name}: {result.error_message}')
        return len(image_files), invalid_count, errors

    def __validate_json_directory(
        self,
        subdir: str,
        count_attr: Optional[str],
        context_name: str,
        exclude_pattern: Optional[str] = None,
        check_anomalies: bool = True,
    ):
        dir_path = PathManager(self.series_name).get_episode_dir(self.episode_info, subdir)
        count, sizes, errors = self.__validate_json_files_in_directory(dir_path, exclude_pattern)
        if not dir_path.exists():
            self.warnings.append(f'Missing {subdir} directory')
            return
        if count == 0:
            self.warnings.append(f'No JSON files in {subdir}/')
            return
        if count_attr:
            setattr(self, count_attr, count)
        self.errors.extend(errors)
        if check_anomalies:
            self.__check_size_anomalies(sizes, context_name)

    @staticmethod
    def __validate_json_files_in_directory(
        directory: Path, exclude_pattern: Optional[str] = None,
    ) -> Tuple[int, List[int], List[str]]:
        if not directory.exists():
            return 0, [], []
        json_files = [
            f for f in directory.glob('*.json')
            if not exclude_pattern or exclude_pattern not in str(f)
        ]
        if not json_files:
            return 0, [], []
        sizes = []
        errors = []
        for json_file in json_files:
            result = FileValidator.validate_json_file(json_file)
            if not result.is_valid:
                errors.append(f'Invalid JSON {json_file.name}: {result.error_message}')
            else:
                sizes.append(json_file.stat().st_size)
        return len(json_files), sizes, errors

    def __validate_object_detections(self):
        self.__validate_json_directory(
            settings.output_subdirs.object_detections,
            'object_detections_count',
            'object_detections',
            exclude_pattern='visualizations',
        )

    def __validate_object_visualizations(self):
        self.__validate_visualizations(settings.output_subdirs.object_visualizations, 'object_visualizations_count', 'visualization')

    def __validate_other_files(self):
        char_detections_dir = PathManager(self.series_name).get_episode_dir(self.episode_info, settings.output_subdirs.character_detections)
        detections_file = char_detections_dir / OUTPUT_FILE_NAMES['detections']
        if detections_file.exists():
            result = FileValidator.validate_json_file(detections_file)
            if not result.is_valid:
                self.errors.append(f"Invalid {OUTPUT_FILE_NAMES['detections']}: {result.error_message}")
        embeddings_dir = PathManager(self.series_name).get_episode_dir(self.episode_info, settings.output_subdirs.embeddings)
        if embeddings_dir.exists():
            embeddings_file = embeddings_dir / OUTPUT_FILE_NAMES['embeddings_text']
            if embeddings_file.exists():
                result = FileValidator.validate_json_file(embeddings_file)
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
            elastic_base = settings.output_subdirs.elastic_documents
            elastic_docs_dir = PathManager(self.series_name).get_episode_dir(
                self.episode_info, f'{elastic_base}/{subdir}',
            )
            if elastic_docs_dir.exists():
                found_elastic_docs = True
                for jsonl_file in elastic_docs_dir.glob('*.jsonl'):
                    result = FileValidator.validate_jsonl_file(jsonl_file)
                    if not result.is_valid:
                        self.errors.append(f'Invalid JSONL {jsonl_file.name}: {result.error_message}')
                    else:
                        self.__validate_embedding_dimensions(jsonl_file, subdir)
        if not found_elastic_docs:
            self.warnings.append(f'Missing {settings.output_subdirs.elastic_documents} directory')
        transcriptions_dir = PathManager(self.series_name).get_episode_dir(self.episode_info, settings.output_subdirs.transcriptions)
        if transcriptions_dir.exists():
            clean_subdir = settings.output_subdirs.transcription_subdirs.clean
            clean_dir = transcriptions_dir / clean_subdir
            filename = f'{self.series_name}_{self.episode_info.episode_code()}_text_stats.json'
            text_stats_file = clean_dir / filename
            if text_stats_file.exists():
                result = FileValidator.validate_json_file(text_stats_file)
                if not result.is_valid:
                    self.errors.append(f'Invalid text_stats JSON: {result.error_message}')
            else:
                self.warnings.append(f'Missing text statistics file: {text_stats_file.name}')

    def __validate_raw_transcription(self, transcription_files: Dict[str, Path]):
        raw_transcription = None
        for key in ('main', 'segmented', 'simple'):
            if transcription_files[key].exists():
                raw_transcription = transcription_files[key]
                break
        if not raw_transcription:
            self.warnings.append('Missing raw transcription file (checked: .json, _segmented.json, _simple.json)')
            return
        result = FileValidator.validate_json_file(raw_transcription)
        if not result.is_valid:
            self.errors.append(f'Invalid transcription JSON: {result.error_message}')
            return
        self.__extract_transcription_stats(raw_transcription)

    def __validate_scenes(self):
        scenes_dir = PathManager(self.series_name).get_episode_dir(self.episode_info, settings.output_subdirs.scenes)
        scenes_file = scenes_dir / f"{self.series_name}_{self.episode_info.episode_code()}{OUTPUT_FILE_PATTERNS['scenes_suffix']}"
        if not scenes_file.exists():
            self.errors.append(f'Missing scenes file: {scenes_file}')
            return
        result = FileValidator.validate_json_file(scenes_file)
        if not result.is_valid:
            self.errors.append(f'Invalid scenes JSON: {result.error_message}')
            return
        data = self.__load_json_safely(scenes_file)
        if not data:
            self.errors.append(f'Error reading scenes: {scenes_file}')
            return
        self.scenes_count = data.get('total_scenes', 0)
        scenes = data.get('scenes', [])
        if scenes:
            durations = [scene.get('duration', 0) for scene in scenes]
            self.scenes_avg_duration = round(sum(durations) / len(durations), 2)

    def __validate_sound_events(self, sound_events_file):
        if not sound_events_file.exists():
            self.warnings.append(f'Missing sound events file: {sound_events_file.name}')
            return
        result = FileValidator.validate_json_file(sound_events_file)
        if not result.is_valid:
            self.warnings.append(f'Invalid sound events JSON: {result.error_message}')

    def __validate_transcription(self):
        transcriptions_dir = PathManager(self.series_name).get_episode_dir(self.episode_info, settings.output_subdirs.transcriptions)
        base_name = f'{self.series_name}_{self.episode_info.episode_code()}'
        raw_dir = transcriptions_dir / settings.output_subdirs.transcription_subdirs.raw
        clean_dir = transcriptions_dir / settings.output_subdirs.transcription_subdirs.clean
        sound_events_dir = transcriptions_dir / settings.output_subdirs.transcription_subdirs.sound_events
        transcription_files = {
            'main': raw_dir / f'{base_name}.json',
            'segmented': raw_dir / f'{base_name}_segmented.json',
            'simple': raw_dir / f'{base_name}_simple.json',
            'clean': clean_dir / f'{base_name}_clean_transcription.json',
            'clean_txt': clean_dir / f'{base_name}_clean_transcription.txt',
            'sound_events': sound_events_dir / f'{base_name}_sound_events.json',
        }
        if not any((f.exists() for f in transcription_files.values())):
            self.errors.append('No transcription files found in any format')
            return
        self.__validate_raw_transcription(transcription_files)
        self.__validate_clean_transcription(transcription_files['clean'])
        self.__validate_clean_txt(transcription_files['clean_txt'])
        self.__validate_sound_events(transcription_files['sound_events'])

    def __validate_video(self):
        filename = f'{self.series_name.lower()}_{self.episode_info.episode_code()}{DEFAULT_VIDEO_EXTENSION}'
        season_dir = get_base_output_dir(self.series_name) / settings.output_subdirs.video / self.episode_info.season_code()
        video_file = season_dir / filename
        if not video_file.exists():
            self.warnings.append(f'Missing video file: {video_file}')
            return
        result = FileValidator.validate_video_file(video_file)
        if not result.is_valid:
            self.errors.append(f'Invalid video: {result.error_message}')
            return
        self.video_size_mb = result.metadata['size_mb']
        self.video_duration = result.metadata['duration']
        self.video_codec = result.metadata['codec']
        self.video_resolution = (result.metadata['width'], result.metadata['height'])

    def __validate_visualizations(self, subdir: str, count_attr: str, context_name: str):
        viz_dir = PathManager(self.series_name).get_episode_dir(self.episode_info, subdir)
        total_count, invalid_count, errors = self.__validate_images_in_directory(viz_dir)
        if total_count == 0 and viz_dir.exists():
            self.warnings.append(f'No visualization images in {subdir}/')
            return
        if total_count > 0:
            setattr(self, count_attr, total_count)
            self.errors.extend(errors)
            if invalid_count > 0:
                self.warnings.append(f'{invalid_count} invalid {context_name} images found')

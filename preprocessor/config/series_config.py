from dataclasses import dataclass
import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)


def __deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = base.copy()
    for key, value in override.items():
        if key.startswith('_'):
            continue
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = __deep_merge(result[key], value)
        else:
            result[key] = value
    return result


@dataclass
class EpisodeScrapingConfig:
    parser_mode: str
    urls: List[str]


@dataclass
class CharacterScrapingConfig:
    parser_mode: str
    urls: List[str]


@dataclass
class CharacterReferencesConfig:
    images_per_character: int
    search_engine: str


@dataclass
class ScrapingConfig:
    character_references: CharacterReferencesConfig
    characters: CharacterScrapingConfig
    episodes: EpisodeScrapingConfig


@dataclass
class TranscriptionProcessingConfig:
    device: str
    language: str
    mode: str
    model: str


@dataclass
class TranscodeProcessingConfig:
    bufsize_mbps: float
    codec: str
    force_deinterlace: bool
    gop_size: float
    maxrate_mbps: float
    minrate_mbps: float
    resolution: str
    video_bitrate_mbps: float


@dataclass
class SceneDetectionProcessingConfig:
    min_scene_len: int
    threshold: float


@dataclass
class FrameExportProcessingConfig:
    frames_per_scene: int


@dataclass
class ProcessingConfig:
    frame_export: FrameExportProcessingConfig
    scene_detection: SceneDetectionProcessingConfig
    transcode: TranscodeProcessingConfig
    transcription: TranscriptionProcessingConfig


@dataclass
class ElasticsearchIndexingConfig:
    append: bool
    dry_run: bool
    host: str
    index_name: str


@dataclass
class IndexingConfig:
    elasticsearch: ElasticsearchIndexingConfig


@dataclass
class SeriesConfig:
    display_name: str
    indexing: IndexingConfig
    pipeline_mode: str
    processing: ProcessingConfig
    scraping: ScrapingConfig
    series_name: str
    skip_steps: List[str]

    @staticmethod
    def load(series_name: str) -> 'SeriesConfig':
        config_dir: Path = Path('preprocessor/series_configs')
        config_path: Path = config_dir / f'{series_name}.json'

        return SeriesConfig.__load_from_file(config_path)

    @staticmethod
    def __load_defaults() -> Dict[str, Any]:
        defaults_path: Path = Path('preprocessor/series_configs/defaults.json')
        if not defaults_path.exists():
            return {}
        with open(defaults_path, 'r', encoding='utf-8') as f:
            data: Dict[str, Any] = json.load(f)
        return {k: v for k, v in data.items() if not k.startswith('_')}

    @staticmethod
    def __load_from_dict(data: Dict[str, Any]) -> 'SeriesConfig':
        return SeriesConfig(
            series_name=data['series_name'],
            display_name=data['display_name'],
            pipeline_mode=data.get('pipeline_mode', 'full'),
            skip_steps=data.get('skip_steps', []),
            scraping=ScrapingConfig(
                episodes=EpisodeScrapingConfig(
                    urls=data['scraping']['episodes']['urls'],
                    parser_mode=data['scraping']['episodes']['parser_mode'],
                ),
                characters=CharacterScrapingConfig(
                    urls=data['scraping']['characters']['urls'],
                    parser_mode=data['scraping']['characters']['parser_mode'],
                ),
                character_references=CharacterReferencesConfig(
                    search_engine=data['scraping']['character_references']['search_engine'],
                    images_per_character=data['scraping']['character_references']['images_per_character'],
                ),
            ),
            processing=ProcessingConfig(
                transcription=TranscriptionProcessingConfig(
                    mode=data['processing']['transcription']['mode'],
                    model=data['processing']['transcription']['model'],
                    language=data['processing']['transcription']['language'],
                    device=data['processing']['transcription']['device'],
                ),
                transcode=TranscodeProcessingConfig(
                    codec=data['processing']['transcode']['codec'],
                    resolution=data['processing']['transcode']['resolution'],
                    video_bitrate_mbps=data['processing']['transcode']['video_bitrate_mbps'],
                    minrate_mbps=data['processing']['transcode']['minrate_mbps'],
                    maxrate_mbps=data['processing']['transcode']['maxrate_mbps'],
                    bufsize_mbps=data['processing']['transcode']['bufsize_mbps'],
                    gop_size=data['processing']['transcode']['gop_size'],
                    force_deinterlace=data['processing']['transcode']['force_deinterlace'],
                ),
                scene_detection=SceneDetectionProcessingConfig(
                    threshold=data['processing']['scene_detection']['threshold'],
                    min_scene_len=data['processing']['scene_detection']['min_scene_len'],
                ),
                frame_export=FrameExportProcessingConfig(
                    frames_per_scene=data['processing']['frame_export']['frames_per_scene'],
                ),
            ),
            indexing=IndexingConfig(
                elasticsearch=ElasticsearchIndexingConfig(
                    index_name=data['indexing']['elasticsearch']['index_name'],
                    host=data['indexing']['elasticsearch']['host'],
                    dry_run=data['indexing']['elasticsearch']['dry_run'],
                    append=data['indexing']['elasticsearch']['append'],
                ),
            ),
        )

    @staticmethod
    def __load_from_file(config_path: Path) -> 'SeriesConfig':
        if not config_path.exists():
            raise FileNotFoundError(
                f"Series config not found: {config_path}\n"
                f"Create it using template: preprocessor/series_configs/template.json",
            )

        defaults: Dict[str, Any] = SeriesConfig.__load_defaults()

        with open(config_path, 'r', encoding='utf-8') as f:
            series_overrides: Dict[str, Any] = json.load(f)

        series_filtered: Dict[str, Any] = {
            k: v for k, v in series_overrides.items()
            if not k.startswith('_')
        }

        merged_config: Dict[str, Any] = __deep_merge(defaults, series_filtered)

        return SeriesConfig.__load_from_dict(merged_config)

import logging
from pathlib import Path
import tempfile
from typing import (
    Any,
    Dict,
    List,
)

from preprocessor.config.config import settings
from preprocessor.core.base_processor import (
    BaseProcessor,
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.episode_manager import EpisodeManager
from preprocessor.transcription.generators.multi_format_generator import MultiFormatGenerator
from preprocessor.transcription.processors.audio_normalizer import AudioNormalizer
from preprocessor.transcription.processors.normalized_audio_processor import NormalizedAudioProcessor


class TranscriptionGenerator(BaseProcessor):
    def __init__(self, args: Dict[str, Any]) -> None:
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=2,
            loglevel=logging.DEBUG,
        )

        self.input_videos: Path = Path(self._args["videos"])
        self.series_name_lower: str = self._args.get("name", "unknown").lower()
        self.episodes_info_json: Path = Path(self._args["episodes_info_json"])
        self.episode_manager = EpisodeManager(self.episodes_info_json, self.series_name_lower)

        self.temp_dir = None
        self.audio_normalizer = None
        self.audio_processor = None
        self.multi_format_generator = None
        self.final_output_dir = None

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if "videos" not in args:
            raise ValueError("videos path is required")
        if "episodes_info_json" not in args:
            raise ValueError("episodes_info_json is required")

        videos_path = Path(args["videos"])
        if not videos_path.is_dir():
            raise NotADirectoryError(f"Input videos is not a directory: '{videos_path}'")

    def _get_processing_items(self) -> List[ProcessingItem]:
        if self._check_all_transcriptions_exist():
            return []

        return [
            ProcessingItem(
                episode_id="transcription_batch",
                input_path=self.input_videos,
                metadata={},
            ),
        ]

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        video_files = []
        for ext in self.SUPPORTED_VIDEO_EXTENSIONS:
            video_files.extend(self.input_videos.rglob(f"*{ext}"))
        outputs = []

        for video_file in video_files:
            episode_info = self.episode_manager.parse_filename(video_file)
            if not episode_info:
                continue

            filename = f"{self.series_name_lower}_{episode_info.episode_code()}.json"
            expected_file = self.episode_manager.build_episode_output_path(
                episode_info,
                settings.output_subdirs.transcriptions,
                filename,
            )
            outputs.append(OutputSpec(path=expected_file, required=True))

        return outputs

    def _process_item(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> None:
        ramdisk_path = self._args.get("ramdisk_path")
        if ramdisk_path and Path(ramdisk_path).exists():
            self.temp_dir = tempfile.TemporaryDirectory(dir=str(ramdisk_path))
        else:
            self.temp_dir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with

        try:
            missing_video_files = self._get_missing_video_files(missing_outputs)
            self._init_workers(self._args, missing_video_files)

            self.logger.info("Step 1/3: Normalizing audio from videos...")
            self.audio_normalizer()

            self.logger.info("Step 2/3: Generating transcriptions with Whisper...")
            self.audio_processor()

            self.logger.info("Cleaning up Whisper model...")
            self.audio_processor.cleanup()

            self.logger.info("Step 3/3: Generating multi-format output...")
            self.multi_format_generator()

        except (RuntimeError, OSError, ValueError) as e:
            self.logger.error(f"Error generating transcriptions: {e}")
        finally:
            if self.temp_dir:
                self.temp_dir.cleanup()

    def _check_all_transcriptions_exist(self) -> bool:
        if not self.episodes_info_json.exists():
            self.logger.debug(f"Episodes info JSON not found: {self.episodes_info_json}")
            return False

        video_files = []
        for ext in self.SUPPORTED_VIDEO_EXTENSIONS:
            video_files.extend(self.input_videos.rglob(f"*{ext}"))
        if not video_files:
            self.logger.debug("No video files found to check")
            return False

        missing_files = []
        for video_file in video_files:
            episode_info = self.episode_manager.parse_filename(video_file)
            if not episode_info:
                continue

            filename = f"{self.series_name_lower}_{episode_info.episode_code()}.json"
            expected_file = self.episode_manager.build_episode_output_path(
                episode_info,
                settings.output_subdirs.transcriptions,
                filename,
            )

            if not expected_file.exists():
                missing_files.append(f"{video_file.name} -> {expected_file}")

        if missing_files:
            self.logger.debug(f"Missing {len(missing_files)} transcription(s), first: {missing_files[0]}")
            return False

        self.logger.info(f"All transcriptions already exist for {len(video_files)} video(s)")
        return True

    def _get_missing_video_files(self, missing_outputs: List[OutputSpec]) -> List[Path]:
        video_files = []
        for ext in self.SUPPORTED_VIDEO_EXTENSIONS:
            video_files.extend(self.input_videos.rglob(f"*{ext}"))

        missing_video_files = []

        for video_file in video_files:
            episode_info = self.episode_manager.parse_filename(video_file)
            if not episode_info:
                continue

            filename = f"{self.series_name_lower}_{episode_info.episode_code()}.json"
            expected_file = self.episode_manager.build_episode_output_path(
                episode_info,
                settings.output_subdirs.transcriptions,
                filename,
            )

            if any(expected_file == output.path for output in missing_outputs):
                missing_video_files.append(video_file)

        return missing_video_files

    def _init_workers(self, args: Dict[str, Any], video_files: List[Path]) -> None:
        temp_dir_path: Path = Path(self.temp_dir.name) / "transcription_generator"
        normalizer_output: Path = temp_dir_path / "normalizer"
        processor_output: Path = temp_dir_path / "processor"

        self.final_output_dir: Path = Path(args["transcription_jsons"])

        audio_files = [normalizer_output / video.with_suffix(".wav").name for video in video_files]

        self.audio_normalizer: AudioNormalizer = AudioNormalizer(
            input_videos=self.input_videos,
            output_dir=normalizer_output,
            logger=self.logger,
            video_files=video_files if video_files else None,
        )

        self.audio_processor: NormalizedAudioProcessor = NormalizedAudioProcessor(
            input_audios=normalizer_output,
            output_dir=processor_output,
            logger=self.logger,
            language=args["language"],
            model=args["model"],
            device=args["device"],
            audio_files=audio_files if audio_files else None,
        )

        self.multi_format_generator: MultiFormatGenerator = MultiFormatGenerator(
            jsons_dir=processor_output,
            episodes_info_json=self.episodes_info_json,
            output_base_path=self.final_output_dir,
            logger=self.logger,
            series_name=args["name"],
        )

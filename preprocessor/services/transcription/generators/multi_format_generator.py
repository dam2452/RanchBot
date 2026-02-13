import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    Literal,
    Optional,
)

from preprocessor.config.output_paths import get_base_output_dir
from preprocessor.config.settings_instance import settings
from preprocessor.services.core.logging import ErrorHandlingLogger
from preprocessor.services.episodes import EpisodeManager
from preprocessor.services.transcription.generators.json_generator import JsonGenerator
from preprocessor.services.transcription.generators.srt_generator import SrtGenerator
from preprocessor.services.transcription.generators.txt_generator import TxtGenerator


class MultiFormatGenerator:
    def __init__(
            self,
            jsons_dir: Path,
            episodes_info_json: Path,
            _output_base_path: Path,
            logger: ErrorHandlingLogger,
            series_name: str = '',
    ) -> None:
        self.__jsons_dir = jsons_dir
        self.__logger = logger
        self.__series_name = series_name.lower() if series_name else 'unknown'
        self.__episode_manager = EpisodeManager(episodes_info_json, self.__series_name, logger)

    def __call__(self) -> None:
        for transcription_file in self.__jsons_dir.rglob('*.json'):
            self.__process_transcription_file(transcription_file)

    def __process_transcription_file(self, file_path: Path) -> None:
        try:
            transcription = self.__load_json(file_path)
            if not transcription:
                return

            episode_info = self.__episode_manager.parse_filename(file_path)
            if not episode_info:
                self.__logger.error(f'Cannot extract episode info from {file_path.name}')
                return

            if self.__is_already_processed(episode_info):
                return

            self.__generate_all_formats(transcription, episode_info)
        except Exception as e:
            self.__logger.error(f'Error processing {file_path.name}: {e}')

    def __generate_all_formats(self, transcription: Dict[str, Any], episode_info: Any) -> None:
        base_dir = self.__get_raw_output_dir(episode_info)
        base_dir.mkdir(parents=True, exist_ok=True)

        metadata = EpisodeManager.get_metadata(episode_info)
        full_data = {'episode_info': metadata, **transcription}

        # Generowanie formatów
        self.__save_json(full_data, episode_info, base_dir, 'full')
        self.__save_json(transcription, episode_info, base_dir, 'segmented')
        self.__save_json(transcription, episode_info, base_dir, 'simple')
        self.__save_srt(transcription, episode_info, base_dir)
        self.__save_txt(transcription, episode_info, base_dir)

    def __save_json(
            self, data: Dict[str, Any], ep_info: Any, out_dir: Path,
            fmt: Literal['full', 'simple', 'segmented'],
    ) -> None:
        gen = JsonGenerator(fmt, Path(''), out_dir, self.__logger)
        filename = self.__episode_manager.path_manager.build_filename(
            ep_info, extension='json', suffix=fmt if fmt != 'full' else None,
        )

        converted = gen.convert(data)
        if fmt != 'full':
            converted['episode_info'] = {'season': ep_info.season, 'episode_number': ep_info.relative_episode}
        else:
            converted['episode_info'] = data.get('episode_info', {})

        with open(out_dir / filename, 'w', encoding='utf-8') as f:
            json.dump(converted, f, indent=2, ensure_ascii=False)

    def __save_srt(self, data: Dict[str, Any], ep_info: Any, out_dir: Path) -> None:
        gen = SrtGenerator(Path(''), out_dir, self.__logger)
        filename = self.__episode_manager.path_manager.build_filename(ep_info, extension='srt')
        (out_dir / filename).write_text(gen.convert_to_srt_format(data), encoding='utf-8')

    def __save_txt(self, data: Dict[str, Any], ep_info: Any, out_dir: Path) -> None:
        gen = TxtGenerator(Path(''), out_dir, self.__logger)
        filename = self.__episode_manager.path_manager.build_filename(ep_info, extension='txt')
        (out_dir / filename).write_text(gen.convert_to_txt_format(data), encoding='utf-8')

    def __is_already_processed(self, ep_info: Any) -> bool:
        filename = self.__episode_manager.path_manager.build_filename(ep_info, extension='json')
        target = self.__get_raw_output_dir(ep_info) / filename
        if target.exists():
            self.__logger.info(f'Skipping existing: {ep_info.episode_code()}')
            return True
        return False

    def __get_raw_output_dir(self, ep_info: Any) -> Path:
        return (
            get_base_output_dir(self.__series_name) /
            settings.output_subdirs.transcriptions /
            ep_info.season_code() /
            ep_info.episode_num() / 'raw'
        )

    def __load_json(self, path: Path) -> Optional[Dict[str, Any]]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.__logger.error(f'Load error {path.name}: {e}')
            return None

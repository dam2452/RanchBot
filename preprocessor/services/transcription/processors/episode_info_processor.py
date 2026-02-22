import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    Tuple,
)

from preprocessor.services.core.logging import ErrorHandlingLogger
from preprocessor.services.episodes import EpisodeManager


class EpisodeInfoProcessor:
    def __init__(
            self,
            jsons_dir: Path,
            episodes_info_json: Path,
            output_path: Path,
            logger: ErrorHandlingLogger,
            series_name: str = '',
    ) -> None:
        self.__jsons_dir = jsons_dir
        self.__output_path = output_path
        self.__logger = logger
        self.__series_name = self.__resolve_series_name(series_name)

        self.__output_path.mkdir(parents=True, exist_ok=True)
        self.__episode_manager = EpisodeManager(episodes_info_json, self.__series_name, self.__logger)

    def __call__(self) -> None:
        for transcription_file in self.__jsons_dir.rglob('*.json'):
            self.__process_file(transcription_file)

    def __resolve_series_name(self, series_name: str) -> str:
        if not series_name:
            name = self.__output_path.parent.name.lower()
            self.__logger.warning(f"Using fallback series name from folder: '{name}'")
            return name
        return series_name.lower()

    def __process_file(self, transcription_file: Path) -> None:
        try:
            transcription = self.__load_json(transcription_file)
            episode_info = self.__episode_manager.parse_filename(transcription_file)

            if not episode_info:
                self.__logger.error(f'Failed to parse episode info: {transcription_file.name}')
                return

            _, new_name = self.__write_structured_json(transcription, episode_info)
            self.__sync_original_filename(transcription_file, new_name)
        except Exception as e:
            self.__logger.error(f'Error processing {transcription_file.name}: {e}')

    def __write_structured_json(self, transcription: Dict[str, Any], episode_info) -> Tuple[Path, str]:
        new_name = self.__episode_manager.path_manager.build_filename(episode_info, extension='json')
        target_path = self.__output_path / episode_info.season_code() / new_name
        target_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            'episode_info': EpisodeManager.get_metadata(episode_info),
            'segments': transcription.get('segments', []),
        }

        with target_path.open('w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=4)

        return target_path, new_name

    def __sync_original_filename(self, original_path: Path, new_name: str) -> None:
        target_path = original_path.parent / new_name
        if original_path.name == new_name:
            return

        if target_path.exists():
            self.__logger.error(f'Rename conflict: {target_path} already exists!')
        else:
            original_path.rename(target_path)

    @staticmethod
    def __load_json(path: Path) -> Dict[str, Any]:
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)

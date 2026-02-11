import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    Tuple,
)

from preprocessor.lib.core.logging import ErrorHandlingLogger
from preprocessor.lib.episodes import EpisodeManager


class EpisodeInfoProcessor:

    def __init__(self, jsons_dir: Path, episodes_info_json: Path, output_path: Path, logger: ErrorHandlingLogger, series_name: str=''):
        self.__jsons_dir: Path = jsons_dir
        self.__output_path: Path = output_path
        self.__logger: ErrorHandlingLogger = logger
        if not series_name:
            series_name = self.__output_path.parent.name.lower()
            self.__logger.warning(f"No series name provided. Using fallback from folder name: '{series_name}'")
        self.__series_name: str = series_name.lower()
        self.__output_path.mkdir(parents=True, exist_ok=True)
        self.__episode_manager = EpisodeManager(episodes_info_json, self.__series_name, self.__logger)

    def __call__(self) -> None:
        for transcription_file in self.__jsons_dir.rglob('*.json'):
            self.__process_file(transcription_file)

    @staticmethod
    def __load_transcription(path: Path) -> Dict[str, Any]:
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)

    def __process_file(self, transcription_file: Path) -> None:
        try:
            transcription = self.__load_transcription(transcription_file)
            episode_info = self.__episode_manager.parse_filename(transcription_file)
            if not episode_info:
                self.__logger.error(f'Cannot extract episode info from {transcription_file.name}')
                return
            _, new_json_name = self.__write_episode_json(transcription, episode_info)
            self.__rename_original_file(transcription_file, new_json_name)
        except Exception as e:
            self.__logger.error(f'Error processing file {transcription_file}: {e}')

    def __rename_original_file(self, original_path: Path, new_name: str) -> None:
        new_src = original_path.parent / new_name
        if original_path.name == new_name:
            self.__logger.info(f'File {original_path} already has correct name.')
        elif new_src.exists():
            self.__logger.error(f'Cannot rename {original_path} -> {new_src}, file already exists!')
        else:
            original_path.rename(new_src)
            self.__logger.info(f'Renamed source transcription file: {original_path} -> {new_src}')

    def __write_episode_json(self, transcription: Dict[str, Any], episode_info) -> Tuple[Path, str]:
        new_json_name = self.__episode_manager.path_manager.build_filename(episode_info, extension='json')
        season_dir = self.__output_path / episode_info.season_code()
        output_path = season_dir / new_json_name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result = {'episode_info': EpisodeManager.get_metadata(episode_info), 'segments': transcription.get('segments', [])}
        with output_path.open('w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        self.__logger.info(f'Created episode info {output_path}.')
        return (output_path, new_json_name)

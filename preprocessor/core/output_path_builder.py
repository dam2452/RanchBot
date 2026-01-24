from pathlib import Path

from preprocessor.config.config import (
    BASE_OUTPUT_DIR,
    settings,
)


class OutputPathBuilder:
    @staticmethod
    def get_episode_dir(episode_info, base_subdir: str) -> Path:
        season_code = f"S{episode_info.season:02d}"
        episode_code = f"E{episode_info.relative_episode:02d}"
        return BASE_OUTPUT_DIR / base_subdir / season_code / episode_code

    @staticmethod
    def get_season_dir(episode_info) -> str:
        return "Specjalne" if episode_info.season == 0 else f"S{episode_info.season:02d}"

    @staticmethod
    def build_transcription_path(episode_info, filename: str, subdir: str = "raw") -> Path:
        season_code = f"S{episode_info.season:02d}"
        episode_code = f"E{episode_info.relative_episode:02d}"
        path = BASE_OUTPUT_DIR / settings.output_subdirs.transcriptions / season_code / episode_code / subdir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def build_output_path(episode_info, subdir: str, filename: str) -> Path:
        path = OutputPathBuilder.get_episode_dir(episode_info, subdir) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def build_video_path(episode_info, series_name: str, extension: str = ".mp4") -> Path:
        filename = f"{series_name.lower()}_{episode_info.episode_code()}{extension}"
        season_dir_name = OutputPathBuilder.get_season_dir(episode_info)
        season_dir = BASE_OUTPUT_DIR / settings.output_subdirs.video / season_dir_name
        season_dir.mkdir(parents=True, exist_ok=True)
        return season_dir / filename

    @staticmethod
    def build_elastic_video_path(episode_info, series_name: str) -> str:
        filename = f"{series_name.lower()}_{episode_info.episode_code()}.mp4"
        season_dir_name = OutputPathBuilder.get_season_dir(episode_info)
        path = Path("bot") / f"{series_name.upper()}-WIDEO" / season_dir_name / filename
        return path.as_posix()

    @staticmethod
    def build_embedding_path(episode_info, filename: str) -> Path:
        return OutputPathBuilder.build_output_path(
            episode_info,
            settings.output_subdirs.embeddings,
            filename,
        )

    @staticmethod
    def build_scene_path(episode_info, filename: str) -> Path:
        return OutputPathBuilder.build_output_path(
            episode_info,
            settings.output_subdirs.scenes,
            filename,
        )

    @staticmethod
    def build_elastic_document_path(episode_info, subdoc_type: str, filename: str) -> Path:
        full_subdir = f"{settings.output_subdirs.elastic_documents}/{subdoc_type}"
        return OutputPathBuilder.build_output_path(episode_info, full_subdir, filename)

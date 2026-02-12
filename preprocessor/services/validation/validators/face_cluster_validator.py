import json
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Optional,
)

from preprocessor.config.settings_instance import settings
from preprocessor.services.io.path_service import PathService
from preprocessor.services.validation.file_validators import FileValidator
from preprocessor.services.validation.validators.base_validator import BaseValidator

if TYPE_CHECKING:
    from preprocessor.services.validation.episode_stats import EpisodeStats


class FaceClusterValidator(BaseValidator):

    def validate(self, stats: 'EpisodeStats') -> None:
        clusters_dir = PathService(stats.series_name).get_episode_dir(
            stats.episode_info, settings.output_subdirs.face_clusters,
        )

        if not clusters_dir.exists():
            return

        metadata_files = list(clusters_dir.glob('*_face_clusters.json'))
        metadata_file = metadata_files[0] if metadata_files else None

        if not metadata_file or not metadata_file.exists():
            self._add_warning(stats, 'Missing face clustering metadata file')
            return

        result = FileValidator.validate_json_file(metadata_file)
        if not result.is_valid:
            self._add_error(stats, f'Invalid face clustering metadata: {result.error_message}')
            return

        data = self.__load_json_safely(metadata_file)
        if not data:
            self._add_error(stats, f'Error reading face clustering metadata: {metadata_file}')
            return

        clusters = data.get('clusters', {})
        if isinstance(clusters, dict):
            stats.face_clusters_count = len(clusters)
            total_faces = sum((cluster_info.get('face_count', 0) for cluster_info in clusters.values()))
        elif isinstance(clusters, list):
            stats.face_clusters_count = len(clusters)
            total_faces = sum((cluster_info.get('face_count', 0) for cluster_info in clusters))
        else:
            self._add_warning(stats, 'Unexpected clusters format in face clustering metadata')
            return

        noise_info = data.get('noise', {})
        if noise_info:
            total_faces += noise_info.get('face_count', 0)

        stats.face_clusters_total_faces = total_faces

    @staticmethod
    def __load_json_safely(file_path: Path) -> Optional[Dict[str, Any]]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

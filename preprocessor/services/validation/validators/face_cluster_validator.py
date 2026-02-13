from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Optional,
)

from preprocessor.config.settings_instance import settings
from preprocessor.services.io.path_service import PathService
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

        metadata_file = self.__get_metadata_file(clusters_dir)
        if not metadata_file:
            self._add_warning(stats, 'Missing face clustering metadata file')
            return

        if not self._validate_json_with_error(stats, metadata_file, 'Missing metadata', 'Invalid face metadata'):
            return

        data = self._load_json_safely(metadata_file)
        if data:
            self.__parse_cluster_stats(stats, data)

    def __get_metadata_file(self, clusters_dir: Path) -> Optional[Path]:
        files = list(clusters_dir.glob('*_face_clusters.json'))
        return files[0] if files else None

    def __parse_cluster_stats(self, stats: 'EpisodeStats', data: Dict[str, Any]) -> None:
        clusters = data.get('clusters', {})
        total_faces = 0

        if isinstance(clusters, (dict, list)):
            stats.face_clusters_count = len(clusters)
            items = clusters.values() if isinstance(clusters, dict) else clusters
            total_faces = sum(item.get('face_count', 0) for item in items)
        else:
            self._add_warning(stats, 'Unexpected clusters format in face clustering metadata')
            return

        noise_info = data.get('noise', {})
        total_faces += noise_info.get('face_count', 0)

        stats.face_clusters_total_faces = total_faces

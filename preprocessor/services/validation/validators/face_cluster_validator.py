from __future__ import annotations

from typing import (
    Any,
    Dict,
)

from preprocessor.config.settings_instance import settings
from preprocessor.services.io.path_service import PathService
from preprocessor.services.validation.episode_stats import EpisodeStats
from preprocessor.services.validation.validators.base_validator import BaseValidator


class FaceClusterValidator(BaseValidator):
    def validate(self, stats: EpisodeStats) -> None:
        clusters_file = PathService(stats.series_name).get_episode_file_path(
            stats.episode_info, settings.output_subdirs.face_clusters,
        )

        if not clusters_file.exists():
            return

        if not self._validate_json_with_error(stats, clusters_file, 'Missing face clusters file', 'Invalid face clusters JSON'):
            return

        data = self._load_json_safely(clusters_file)
        if data:
            self.__parse_cluster_stats(stats, data)

    def __parse_cluster_stats(self, stats: EpisodeStats, data: Dict[str, Any]) -> None:
        clusters = data.get('clusters', {})

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

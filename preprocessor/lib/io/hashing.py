from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
)

from preprocessor.config.config import settings
from preprocessor.lib.episodes import EpisodeInfo
from preprocessor.lib.io.files import FileOperations
from preprocessor.lib.io.metadata import MetadataBuilder
from preprocessor.lib.io.path_manager import PathManager


class HashStorage:

    @staticmethod
    def __save_image_hashes_to_json( # pylint: disable=unused-private-member
        episode_info: EpisodeInfo,
        hash_results: List[Dict[str, Any]],
        series_name: str,
        device: str,
        batch_size: int,
    ) -> Path:
        path_manager = PathManager(series_name)
        episode_dir = path_manager.get_episode_dir(
            episode_info,
            settings.output_subdirs.image_hashes,
        )
        episode_dir.mkdir(parents=True, exist_ok=True)
        unique_hashes = len(
            set((
                h.get('perceptual_hash')
                for h in hash_results
                if 'perceptual_hash' in h
            )),
        )
        hash_data = MetadataBuilder.create_processing_metadata(
            episode_info=episode_info,
            processing_params={'device': device, 'batch_size': batch_size, 'hash_size': 8},
            statistics={'total_hashes': len(hash_results), 'unique_hashes': unique_hashes},
            results_key='image_hashes',
            results_data=hash_results,
        )
        hash_filename = path_manager.build_filename(episode_info, extension='json', suffix='image_hashes')
        output_path = episode_dir / hash_filename
        FileOperations.atomic_write_json(output_path, hash_data)
        return output_path

from datetime import datetime
import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    Optional,
)

from preprocessor.services.validation.episode_stats import EpisodeStats
from preprocessor.services.validation.season_comparator import SeasonComparison


class ReportGenerator:
    def __init__(self, season: str, anomaly_threshold: float) -> None:
        self.__season = season
        self.__anomaly_threshold = anomaly_threshold
        self.__timestamp = datetime.now().isoformat()

    def generate_report(
        self,
        episodes_stats: Dict[str, EpisodeStats],
        season_comparison: SeasonComparison,
        output_path: Path,
    ) -> Optional[Dict[str, Any]]:
        report = {
            'validation_timestamp': self.__timestamp,
            'season': self.__season,
            'anomaly_threshold': self.__anomaly_threshold,
            'episodes': {eid: s.to_dict() for eid, s in episodes_stats.items()},
            'season_comparison': season_comparison.to_dict(),
        }
        self.__write_to_disk(report, output_path)
        return report

    @staticmethod
    def __write_to_disk(data: Dict[str, Any], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

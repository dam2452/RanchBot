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
        self.season = season
        self.anomaly_threshold = anomaly_threshold
        self.timestamp = datetime.now().isoformat()

    def generate_report(
        self,
        episodes_stats: Dict[str, EpisodeStats],
        season_comparison: SeasonComparison,
        output_path: Path,
    ) -> Optional[Dict[str, Any]]:
        report = {
            'validation_timestamp': self.timestamp,
            'season': self.season,
            'anomaly_threshold': self.anomaly_threshold,
            'episodes': {
                episode_id: stats.to_dict()
                for episode_id, stats in episodes_stats.items()
            },
            'season_comparison': season_comparison.to_dict(),
        }
        self.__save_report(report, output_path)
        return report

    @staticmethod
    def __save_report(report: Dict[str, Any], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

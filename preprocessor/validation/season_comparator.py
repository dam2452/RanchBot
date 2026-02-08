from dataclasses import (
    dataclass,
    field,
)
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from preprocessor.validation.episode_stats import EpisodeStats


@dataclass
class MetricComparison:
    metric_name: str
    min_value: Optional[float]
    max_value: Optional[float]
    avg_value: Optional[float]
    difference_percent: Optional[float]


@dataclass
class Anomaly:
    episode: str
    metric: str
    value: float
    avg: float
    deviation_percent: float
    severity: str


@dataclass
class SeasonComparison:
    season: str
    anomaly_threshold: float
    metrics: Dict[str, MetricComparison] = field(default_factory=dict)
    anomalies: List[Anomaly] = field(default_factory=list)

    def compare_episodes(self, episodes_stats: Dict[str, EpisodeStats]):
        metric_keys = [
            "transcription_duration",
            "transcription_chars",
            "transcription_words",
            "exported_frames_count",
            "exported_frames_total_size_mb",
            "video_size_mb",
            "video_duration",
            "scenes_count",
        ]

        for metric_key in metric_keys:
            self.__compare_metric(metric_key, episodes_stats)

    def __compare_metric(self, metric_key: str, episodes_stats: Dict[str, EpisodeStats]):
        values = []
        episode_values = {}

        for episode_id, stats in episodes_stats.items():
            value = getattr(stats, metric_key, None)
            if value is not None:
                values.append(value)
                episode_values[episode_id] = value

        if not values:
            return

        min_val = min(values)
        max_val = max(values)
        avg_val = sum(values) / len(values)

        if min_val > 0:
            diff_percent = ((max_val - min_val) / min_val) * 100
        else:
            diff_percent = 0.0

        self.metrics[metric_key] = MetricComparison(
            metric_name=metric_key,
            min_value=round(min_val, 2),
            max_value=round(max_val, 2),
            avg_value=round(avg_val, 2),
            difference_percent=round(diff_percent, 2),
        )

        for episode_id, value in episode_values.items():
            if avg_val > 0:
                deviation_percent = abs((value - avg_val) / avg_val) * 100
            else:
                deviation_percent = 0.0

            if deviation_percent > self.anomaly_threshold:
                severity = "ERROR" if deviation_percent > self.anomaly_threshold * 2 else "WARNING"
                self.anomalies.append(
                    Anomaly(
                        episode=episode_id,
                        metric=metric_key,
                        value=round(value, 2),
                        avg=round(avg_val, 2),
                        deviation_percent=round(deviation_percent, 2),
                        severity=severity,
                    ),
                )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metrics": {
                metric_name: {
                    "min": metric.min_value,
                    "max": metric.max_value,
                    "avg": metric.avg_value,
                    "difference_percent": metric.difference_percent,
                }
                for metric_name, metric in self.metrics.items()
            },
            "anomalies": [
                {
                    "episode": anomaly.episode,
                    "metric": anomaly.metric,
                    "value": anomaly.value,
                    "avg": anomaly.avg,
                    "deviation_percent": anomaly.deviation_percent,
                    "severity": anomaly.severity,
                }
                for anomaly in self.anomalies
            ],
        }

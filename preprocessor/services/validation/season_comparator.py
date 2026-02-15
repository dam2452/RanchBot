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

from preprocessor.services.validation.episode_stats import EpisodeStats


@dataclass
class MetricComparison:
    avg_value: Optional[float]
    difference_percent: Optional[float]
    max_value: Optional[float]
    metric_name: str
    min_value: Optional[float]


@dataclass
class Anomaly:
    avg: float
    deviation_percent: float
    episode: str
    metric: str
    severity: str
    value: float


@dataclass
class SeasonComparison:
    anomaly_threshold: float
    season: str
    anomalies: List[Anomaly] = field(default_factory=list)
    metrics: Dict[str, MetricComparison] = field(default_factory=dict)

    def compare_episodes(self, episodes_stats: Dict[str, EpisodeStats]) -> None:
        metrics_to_check = [
            'transcription_duration', 'transcription_chars', 'transcription_words',
            'exported_frames_count', 'exported_frames_total_size_mb',
            'video_size_mb', 'video_duration', 'scenes_count',
        ]
        for key in metrics_to_check:
            self.__analyze_metric_across_episodes(key, episodes_stats)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'metrics': {
                name: {
                    'min': m.min_value, 'max': m.max_value,
                    'avg': m.avg_value, 'difference_percent': m.difference_percent,
                } for name, m in self.metrics.items()
            },
            'anomalies': [
                {
                    'episode': a.episode, 'metric': a.metric, 'value': a.value,
                    'avg': a.avg, 'deviation_percent': a.deviation_percent, 'severity': a.severity,
                } for a in self.anomalies
            ],
        }

    def __analyze_metric_across_episodes(self, key: str, stats_dict: Dict[str, EpisodeStats]) -> None:
        episode_values = {
            ep_id: val for ep_id, s in stats_dict.items()
            if (val := getattr(s, key, None)) is not None
        }

        if not episode_values:
            return

        values = list(episode_values.values())
        avg_val = sum(values) / len(values)

        self.__calculate_metric_summary(key, values, avg_val)
        self.__detect_anomalies_for_metric(key, episode_values, avg_val)

    def __calculate_metric_summary(self, key: str, values: List[float], avg_val: float) -> None:
        min_v, max_v = min(values), max(values)
        diff = ((max_v - min_v) / min_v * 100) if min_v > 0 else 0.0

        self.metrics[key] = MetricComparison(
            metric_name=key,
            min_value=round(min_v, 2),
            max_value=round(max_v, 2),
            avg_value=round(avg_val, 2),
            difference_percent=round(diff, 2),
        )

    def __detect_anomalies_for_metric(self, key: str, ep_values: Dict[str, float], avg_val: float) -> None:
        if avg_val <= 0:
            return

        for ep_id, val in ep_values.items():
            deviation = abs((val - avg_val) / avg_val) * 100
            if deviation > self.anomaly_threshold:
                self.anomalies.append(self.__create_anomaly_record(ep_id, key, val, avg_val, deviation))

    def __create_anomaly_record(self, ep_id: str, key: str, val: float, avg: float, dev: float) -> Anomaly:
        severity = 'ERROR' if dev > (self.anomaly_threshold * 2) else 'WARNING'
        return Anomaly(
            episode=ep_id, metric=key, value=round(val, 2),
            avg=round(avg, 2), deviation_percent=round(dev, 2), severity=severity,
        )

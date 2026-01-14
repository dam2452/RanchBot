from pathlib import Path
from typing import Dict, Optional

from rich.console import Console
from rich.progress import track

from preprocessor.config.config import BASE_OUTPUT_DIR
from preprocessor.core.constants import OUTPUT_FILE_NAMES
from preprocessor.core.episode_manager import EpisodeInfo, EpisodeManager
from preprocessor.validation.episode_stats import EpisodeStats
from preprocessor.validation.report_generator import ReportGenerator
from preprocessor.validation.season_comparator import SeasonComparison

console = Console()


class Validator:
    def __init__(
        self,
        season: str,
        series_name: str = "ranczo",
        anomaly_threshold: float = 20.0,
        base_output_dir: Path = BASE_OUTPUT_DIR,
        episodes_info_json: Optional[Path] = None,
    ):
        self.season = season
        self.series_name = series_name
        self.anomaly_threshold = anomaly_threshold
        self.base_output_dir = base_output_dir
        self.season_path = base_output_dir / "episodes" / season
        self.episode_manager = EpisodeManager(episodes_info_json, series_name)

    def validate(self, output_report_path: Path) -> int:
        if not self.season_path.exists():
            console.print(f"[red]Season directory not found: {self.season_path}[/red]")
            return 1

        console.print(f"[bold cyan]Validating season {self.season}...[/bold cyan]")

        episodes_stats = self._collect_episodes_stats()

        if not episodes_stats:
            console.print(f"[red]No episodes found in {self.season_path}[/red]")
            return 1

        self._generate_episode_reports(episodes_stats)

        season_comparison = SeasonComparison(
            season=self.season,
            anomaly_threshold=self.anomaly_threshold,
        )
        season_comparison.compare_episodes(episodes_stats)

        report_generator = ReportGenerator(
            season=self.season,
            anomaly_threshold=self.anomaly_threshold,
        )
        report = report_generator.generate_report(episodes_stats, season_comparison, output_report_path)

        self._print_summary(episodes_stats, season_comparison)

        console.print(f"\n[green]Season validation report saved to: {output_report_path}[/green]")
        console.print(f"[green]Individual episode reports saved in each episode directory[/green]")

        return 0

    def _collect_episodes_stats(self) -> Dict[str, EpisodeStats]:
        episode_dirs = sorted([d for d in self.season_path.iterdir() if d.is_dir() and d.name.startswith("E")])

        episodes_stats = {}
        for episode_dir in track(episode_dirs, description="Collecting episode stats"):
            episode_num = int(episode_dir.name[1:])
            season_num = int(self.season[1:])

            episode_info = self.episode_manager.get_episode_by_season_and_relative(season_num, episode_num)
            if not episode_info:
                console.print(f"[yellow]Skipping {episode_dir.name}: could not parse episode info[/yellow]")
                continue

            episode_id = episode_info.episode_code()
            stats = EpisodeStats(
                episode_info=episode_info,
                episode_path=episode_dir,
                series_name=self.series_name,
            )
            stats.collect_stats()
            episodes_stats[episode_id] = stats

        return episodes_stats

    def _generate_episode_reports(self, episodes_stats: Dict[str, EpisodeStats]):
        import json
        from datetime import datetime

        for stats in episodes_stats.values():
            episode_report = {
                "validation_timestamp": datetime.now().isoformat(),
                "episode_id": stats.episode_info.episode_code(),
                "episode_title": stats.episode_info.title,
                "status": stats.status,
                "errors": stats.errors,
                "warnings": stats.warnings,
                "stats": stats.to_dict()["stats"],
            }

            report_path = stats.episode_path / OUTPUT_FILE_NAMES["validation_report"]
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(episode_report, f, indent=2, ensure_ascii=False)

    def _print_summary(self, episodes_stats: Dict[str, EpisodeStats], season_comparison: SeasonComparison):
        console.print(f"\n[bold]Validation Summary for {self.season}[/bold]")
        console.print(f"Total episodes: {len(episodes_stats)}")

        pass_count = sum(1 for stats in episodes_stats.values() if stats.status == "PASS")
        warning_count = sum(1 for stats in episodes_stats.values() if stats.status == "WARNING")
        fail_count = sum(1 for stats in episodes_stats.values() if stats.status == "FAIL")

        console.print(f"  [green]PASS:[/green] {pass_count}")
        console.print(f"  [yellow]WARNING:[/yellow] {warning_count}")
        console.print(f"  [red]FAIL:[/red] {fail_count}")

        if season_comparison.anomalies:
            console.print(f"\n[bold yellow]Anomalies detected: {len(season_comparison.anomalies)}[/bold yellow]")
            for anomaly in season_comparison.anomalies[:5]:
                color = "red" if anomaly.severity == "ERROR" else "yellow"
                console.print(
                    f"  [{color}]{anomaly.episode}[/{color}]: "
                    f"{anomaly.metric} = {anomaly.value} "
                    f"(avg: {anomaly.avg}, deviation: {anomaly.deviation_percent:.1f}%)"
                )
            if len(season_comparison.anomalies) > 5:
                console.print(f"  ... and {len(season_comparison.anomalies) - 5} more")

        for episode_id, stats in episodes_stats.items():
            if stats.errors:
                console.print(f"\n[red]Errors in {episode_id}:[/red]")
                for error in stats.errors[:3]:
                    console.print(f"  - {error}")
                if len(stats.errors) > 3:
                    console.print(f"  ... and {len(stats.errors) - 3} more")

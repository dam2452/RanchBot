from datetime import datetime
from pathlib import Path
from typing import (
    Dict,
    Optional,
)

from rich.console import Console
from rich.progress import track

from preprocessor.config.config import settings
from preprocessor.services.episodes import EpisodeManager
from preprocessor.services.io.files import FileOperations
from preprocessor.services.io.path_manager import PathManager
from preprocessor.services.validation.episode_stats import EpisodeStats
from preprocessor.services.validation.report_generator import ReportGenerator
from preprocessor.services.validation.season_comparator import SeasonComparison

console = Console()

class Validator:

    def __init__(
        self,
        season: str,
        series_name: str = 'ranczo',
        anomaly_threshold: float = 20.0,
        base_output_dir: Path = None,
        episodes_info_json: Optional[Path] = None,
    ):
        self.season = season
        self.series_name = series_name
        self.anomaly_threshold = anomaly_threshold
        self.base_output_dir = base_output_dir
        self.episode_manager = EpisodeManager(episodes_info_json, series_name)
        self.validation_reports_dir = base_output_dir / settings.output_subdirs.validation_reports

    def validate(self) -> int:
        transcriptions_season_path = self.base_output_dir / 'transcriptions' / self.season
        if not transcriptions_season_path.exists():
            console.print(f'[red]Season directory not found: {transcriptions_season_path}[/red]')
            return 1
        console.print(f'[bold cyan]Validating season {self.season}...[/bold cyan]')
        episodes_stats = self.__collect_episodes_stats(transcriptions_season_path)
        if not episodes_stats:
            console.print(f'[red]No episodes found in {transcriptions_season_path}[/red]')
            return 1
        self.validation_reports_dir.mkdir(parents=True, exist_ok=True)
        self.__generate_episode_reports(episodes_stats)
        season_comparison = SeasonComparison(season=self.season, anomaly_threshold=self.anomaly_threshold)
        season_comparison.compare_episodes(episodes_stats)
        report_generator = ReportGenerator(season=self.season, anomaly_threshold=self.anomaly_threshold)
        season_report_path = self.validation_reports_dir / f'{self.series_name}_{self.season}_season.json'
        report_generator.generate_report(episodes_stats, season_comparison, season_report_path)
        self.__print_summary(episodes_stats, season_comparison)
        console.print(f'\n[green]Validation reports saved to: {self.validation_reports_dir}[/green]')
        return 0

    def __collect_episodes_stats(self, transcriptions_season_path: Path) -> Dict[str, EpisodeStats]:
        episode_dirs = sorted([d for d in transcriptions_season_path.iterdir() if d.is_dir() and d.name.startswith('E')])
        episodes_stats = {}
        for episode_dir in track(episode_dirs, description='Collecting episode stats'):
            episode_num = int(episode_dir.name[1:])
            season_num = int(self.season[1:])
            episode_info = self.episode_manager.get_episode_by_season_and_relative(season_num, episode_num)
            if not episode_info:
                console.print(f'[yellow]Skipping {episode_dir.name}: could not parse episode info[/yellow]')
                continue
            episode_id = episode_info.episode_code()
            stats = EpisodeStats(episode_info=episode_info, series_name=self.series_name)
            stats.collect_stats()
            episodes_stats[episode_id] = stats
        return episodes_stats

    def __generate_episode_reports(self, episodes_stats: Dict[str, EpisodeStats]) -> None:
        for stats in episodes_stats.values():
            episode_report = {
                'validation_timestamp': datetime.now().isoformat(),
                'episode_id': stats.episode_info.episode_code(),
                'episode_title': stats.episode_info.title,
                'status': stats.status,
                'errors': stats.errors,
                'warnings': stats.warnings,
                'stats': stats.to_dict()['stats'],
            }
            path_manager = PathManager(self.series_name)
            report_filename = path_manager.build_filename(stats.episode_info, extension='json')
            report_path = self.validation_reports_dir / report_filename
            FileOperations.atomic_write_json(report_path, episode_report)

    def __print_summary(self, episodes_stats: Dict[str, EpisodeStats], season_comparison: SeasonComparison) -> None:
        console.print(f'\n[bold]Validation Summary for {self.season}[/bold]')
        console.print(f'Total episodes: {len(episodes_stats)}')
        pass_count = sum((1 for stats in episodes_stats.values() if stats.status == 'PASS'))
        warning_count = sum((1 for stats in episodes_stats.values() if stats.status == 'WARNING'))
        fail_count = sum((1 for stats in episodes_stats.values() if stats.status == 'FAIL'))
        console.print(f'  [green]PASS:[/green] {pass_count}')
        console.print(f'  [yellow]WARNING:[/yellow] {warning_count}')
        console.print(f'  [red]FAIL:[/red] {fail_count}')
        if season_comparison.anomalies:
            console.print(f'\n[bold yellow]Anomalies detected: {len(season_comparison.anomalies)}[/bold yellow]')
            for anomaly in season_comparison.anomalies[:5]:
                color = 'red' if anomaly.severity == 'ERROR' else 'yellow'
                msg = (
                    f'{anomaly.metric} = {anomaly.value} '
                    f'(avg: {anomaly.avg}, deviation: {anomaly.deviation_percent:.1f}%)'
                )
                console.print(f'  [{color}]{anomaly.episode}[/{color}]: {msg}')
            if len(season_comparison.anomalies) > 5:
                console.print(f'  ... and {len(season_comparison.anomalies) - 5} more')
        for episode_id, stats in episodes_stats.items():
            if stats.errors:
                console.print(f'\n[red]Errors in {episode_id}:[/red]')
                for error in stats.errors[:3]:
                    console.print(f'  - {error}')
                if len(stats.errors) > 3:
                    console.print(f'  ... and {len(stats.errors) - 3} more')
            if stats.warnings:
                console.print(f'\n[yellow]Warnings in {episode_id}:[/yellow]')
                for warning in stats.warnings[:3]:
                    console.print(f'  - {warning}')
                if len(stats.warnings) > 3:
                    console.print(f'  ... and {len(stats.warnings) - 3} more')

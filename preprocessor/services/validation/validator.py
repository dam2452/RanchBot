from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from rich.console import Console
from rich.progress import track

from preprocessor.config.settings_instance import settings
from preprocessor.services.episodes import EpisodeManager
from preprocessor.services.io.files import FileOperations
from preprocessor.services.io.path_service import PathService
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
            base_output_dir: Optional[Path] = None,
            episodes_info_json: Optional[Path] = None,
    ) -> None:
        self.__season = season
        self.__series_name = series_name
        self.__anomaly_threshold = anomaly_threshold
        self.__base_output_dir = base_output_dir
        self.__episode_manager = EpisodeManager(episodes_info_json, series_name)
        self.__validation_reports_dir = base_output_dir / settings.output_subdirs.validation_reports

    def validate(self) -> int:
        transcriptions_path = self.__base_output_dir / 'transcriptions' / self.__season
        if not transcriptions_path.exists():
            console.print(f'[red]Season directory not found: {transcriptions_path}[/red]')
            return 1

        console.print(f'[bold cyan]Validating season {self.__season}...[/bold cyan]')

        episodes_stats = self.__collect_all_episodes_stats(transcriptions_path)
        if not episodes_stats:
            console.print(f'[red]No episodes found in {transcriptions_path}[/red]')
            return 1

        self.__generate_reports_and_compare(episodes_stats)
        return 0

    def __generate_reports_and_compare(self, episodes_stats: Dict[str, EpisodeStats]) -> None:
        self.__validation_reports_dir.mkdir(parents=True, exist_ok=True)

        self.__save_individual_episode_reports(episodes_stats)

        comparison = SeasonComparison(season=self.__season, anomaly_threshold=self.__anomaly_threshold)
        comparison.compare_episodes(episodes_stats)

        self.__generate_season_summary_report(episodes_stats, comparison)
        self.__print_execution_summary(episodes_stats, comparison)

        console.print(f'\n[green]Validation reports saved to: {self.__validation_reports_dir}[/green]')

    def __collect_all_episodes_stats(self, season_path: Path) -> Dict[str, EpisodeStats]:
        episode_dirs = sorted([d for d in season_path.iterdir() if d.is_dir() and d.name.startswith('E')])
        results: Dict[str, EpisodeStats] = {}

        for ep_dir in track(episode_dirs, description='Collecting episode stats'):
            stats = self.__process_single_episode_dir(ep_dir)
            if stats:
                results[stats.episode_info.episode_code()] = stats
        return results

    def __process_single_episode_dir(self, ep_dir: Path) -> Optional[EpisodeStats]:
        try:
            episode_num = int(ep_dir.name[1:])
            season_num = int(self.__season[1:])
            info = self.__episode_manager.get_episode_by_season_and_relative(season_num, episode_num)

            if not info:
                console.print(f'[yellow]Skipping {ep_dir.name}: could not parse info[/yellow]')
                return None

            stats = EpisodeStats(episode_info=info, series_name=self.__series_name)
            stats.collect_stats()
            return stats
        except ValueError:
            return None

    def __save_individual_episode_reports(self, episodes_stats: Dict[str, EpisodeStats]) -> None:
        path_manager = PathService(self.__series_name)
        for stats in episodes_stats.values():
            report = self.__build_episode_report_payload(stats)
            filename = path_manager.build_filename(stats.episode_info, extension='json')
            FileOperations.atomic_write_json(self.__validation_reports_dir / filename, report)

    def __generate_season_summary_report(self, stats: Dict[str, EpisodeStats], comparison: SeasonComparison) -> None:
        generator = ReportGenerator(season=self.__season, anomaly_threshold=self.__anomaly_threshold)
        report_path = self.__validation_reports_dir / f'{self.__series_name}_{self.__season}_season.json'
        generator.generate_report(stats, comparison, report_path)

    def __print_execution_summary(self, stats: Dict[str, EpisodeStats], comparison: SeasonComparison) -> None:
        console.print(f'\n[bold]Validation Summary for {self.__season}[/bold]')
        console.print(f'Total episodes: {len(stats)}')

        self.__print_status_counts(stats)
        self.__print_anomalies(comparison)
        self.__print_issues(stats)

    def __build_episode_report_payload(self, stats: EpisodeStats) -> Dict[str, Any]:
        return {
            'validation_timestamp': datetime.now().isoformat(),
            'episode_id': stats.episode_info.episode_code(),
            'episode_title': stats.episode_info.title,
            'status': stats.status,
            'errors': stats.errors,
            'warnings': stats.warnings,
            'stats': stats.to_dict()['stats'],
        }

    def __print_status_counts(self, stats: Dict[str, EpisodeStats]) -> None:
        counts = {'PASS': 0, 'WARNING': 0, 'FAIL': 0}
        for s in stats.values():
            counts[s.status] += 1
        console.print(f'  [green]PASS:[/green] {counts["PASS"]}')
        console.print(f'  [yellow]WARNING:[/yellow] {counts["WARNING"]}')
        console.print(f'  [red]FAIL:[/red] {counts["FAIL"]}')

    def __print_anomalies(self, comparison: SeasonComparison) -> None:
        if not comparison.anomalies:
            return
        console.print(f'\n[bold yellow]Anomalies detected: {len(comparison.anomalies)}[/bold yellow]')
        for anomaly in comparison.anomalies[:5]:
            color = 'red' if anomaly.severity == 'ERROR' else 'yellow'
            msg = f'{anomaly.metric} = {anomaly.value} (avg: {anomaly.avg}, dev: {anomaly.deviation_percent:.1f}%)'
            console.print(f'  [{color}]{anomaly.episode}[/{color}]: {msg}')

    def __print_issues(self, stats_dict: Dict[str, EpisodeStats]) -> None:
        for ep_id, stats in stats_dict.items():
            if stats.errors:
                self.__print_list('red', f'Errors in {ep_id}', stats.errors)
            if stats.warnings:
                self.__print_list('yellow', f'Warnings in {ep_id}', stats.warnings)

    @staticmethod
    def __print_list(color: str, title: str, items: List[str]) -> None:
        console.print(f'\n[{color}]{title}:[/{color}]')
        for item in items[:3]:
            console.print(f'  - {item}')
        if len(items) > 3:
            console.print(f'  ... and {len(items) - 3} more')

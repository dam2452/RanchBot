# pylint: skip-file
import argparse
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from preprocessor.services.media.scene_detection import TransNetWrapper  # noqa: E402  # pylint: disable=wrong-import-position

_VIDEO_EXTENSIONS: Tuple[str, ...] = ('.mkv', '.mp4', '.avi')
_EP_PATTERN = re.compile(r'(S\d{2})E(\d{2})')
_BLACK_PATTERN = re.compile(r'black_start:([\d.]+)\s+black_end:([\d.]+)')


def _probe_duration(video_path: Path) -> float:
    result = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(video_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=True,
        text=True,
    )
    return float(json.loads(result.stdout)['format']['duration'])


def _detect_scenes(video_path: Path, threshold: float, min_scene_len: int) -> List[Dict[str, Any]]:
    wrapper = TransNetWrapper()
    wrapper.load_model()
    try:
        return wrapper.detect_scenes(video_path, threshold=threshold, min_scene_len=min_scene_len)
    finally:
        wrapper.cleanup()


def _scene_cut_timestamps(scenes: List[Dict[str, Any]]) -> List[float]:
    return [
        float(s['start']['seconds']) if isinstance(s.get('start'), dict) else float(s.get('start', 0))
        for s in scenes[1:]
    ]


def _nearest_cut(cuts: List[float], target: float) -> float:
    return min(cuts, key=lambda t: abs(t - target))


def _detect_black_frames(
        video_path: Path,
        cut: float,
        half_window: float,
        black_duration: float = 0.02,
        pix_threshold: float = 0.10,
) -> List[Tuple[float, float]]:
    scan_start = max(0.0, cut - half_window)
    result = subprocess.run(
        [
            'ffmpeg',
            '-ss', str(scan_start),
            '-t', str(half_window * 2),
            '-i', str(video_path),
            '-vf', f'blackdetect=d={black_duration}:pix_th={pix_threshold}',
            '-an', '-f', 'null', '-',
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return [
        (float(m.group(1)) + scan_start, float(m.group(2)) + scan_start)
        for m in _BLACK_PATTERN.finditer(result.stderr)
    ]


def _adjust_for_black_frames(
        cut: float,
        black_intervals: List[Tuple[float, float]],
        max_distance: float = 5.0,
) -> float:
    best_interval: Optional[Tuple[float, float]] = None
    best_dist = math.inf

    for black_start, black_end in black_intervals:
        if black_start <= cut <= black_end:
            dist = 0.0
        elif black_end < cut:
            dist = cut - black_end
        else:
            dist = black_start - cut

        if dist <= max_distance and dist < best_dist:
            best_dist = dist
            best_interval = (black_start, black_end)

    return best_interval[1] if best_interval is not None else cut


def _classify_file(video_path: Path, half_window: float) -> Tuple[bool, float]:
    midpoint = _probe_duration(video_path) / 2.0
    black_intervals = _detect_black_frames(video_path, midpoint, half_window)
    adjusted = _adjust_for_black_frames(midpoint, black_intervals)
    return adjusted != midpoint or bool(black_intervals), adjusted


def _rename_episode(filename: str, new_ep: int, special: bool = False) -> str:
    match = _EP_PATTERN.search(filename)
    if not match:
        raise ValueError(f'No SxxExx pattern in filename: {filename}')
    season = match.group(1)
    suffix = '_SPECIAL' if special else ''
    replacement = f'{season}E{new_ep:02d}{suffix}'
    return filename[:match.start()] + replacement + filename[match.end():]


def _ffmpeg_split(video_path: Path, cut_time: float, ep1_path: Path, ep2_path: Path) -> None:
    codec = ['-c:v', 'hevc_nvenc', '-preset', 'p4', '-cq', '18', '-c:a', 'copy']
    subprocess.run(
        ['ffmpeg', '-y', '-i', str(video_path), '-t', str(cut_time)] + codec + [str(ep1_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    subprocess.run(
        ['ffmpeg', '-y', '-ss', str(cut_time), '-i', str(video_path)] + codec + [str(ep2_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )


def _split_double(
        video: Path,
        approx_cut: float,
        half_window: float,
        threshold: float,
        min_scene_len: int,
        output_dir: Path,
        ep_counter: int,
) -> int:
    scenes = _detect_scenes(video, threshold, min_scene_len)
    cuts = _scene_cut_timestamps(scenes)
    raw_cut = _nearest_cut(cuts, approx_cut) if cuts else approx_cut
    black_intervals = _detect_black_frames(video, raw_cut, half_window)
    final_cut = _adjust_for_black_frames(raw_cut, black_intervals)

    ep1_name = _rename_episode(video.name, ep_counter)
    ep2_name = _rename_episode(video.name, ep_counter + 1)

    direction = ''
    if final_cut != raw_cut:
        arrow = 'forward' if final_cut > raw_cut else 'backward'
        direction = f' ({arrow} {raw_cut:.3f}s -> {final_cut:.3f}s)'

    print(f'  [SPLIT] {video.name}  cut={final_cut:.3f}s{direction}')
    print(f'    E{ep_counter:02d} -> {ep1_name}')
    print(f'    E{ep_counter + 1:02d} -> {ep2_name}')

    _ffmpeg_split(video, final_cut, output_dir / ep1_name, output_dir / ep2_name)
    return ep_counter + 2


def _process_season(
        season_dir: Path,
        output_dir: Path,
        half_window: float,
        threshold: float,
        min_scene_len: int,
        dry_run: bool,
) -> None:
    videos = sorted(p for p in season_dir.iterdir() if p.suffix.lower() in _VIDEO_EXTENSIONS)
    if not videos:
        print(f'[{season_dir.name}] no videos found')
        return

    print(f'\n[{season_dir.name}] classifying {len(videos)} file(s)...')
    classifications: List[Tuple[Path, bool, float]] = []
    for video in videos:
        is_double, cut = _classify_file(video, half_window)
        label = 'DOUBLE' if is_double else 'SPECIAL'
        cut_info = f'  cut={cut:.3f}s' if is_double else ''
        print(f'  [{label}] {video.name}{cut_info}')
        classifications.append((video, is_double, cut))

    if dry_run:
        specials = [v.name for v, is_double, _ in classifications if not is_double]
        if specials:
            print(f'  --- SPECIALS: {specials}')
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    ep_counter = 1

    for video, is_double, approx_cut in classifications:
        if is_double:
            ep_counter = _split_double(video, approx_cut, half_window, threshold, min_scene_len, output_dir, ep_counter)
        else:
            special_name = _rename_episode(video.name, ep_counter, special=True)
            print(f'  [COPY ] {video.name}')
            print(f'    E{ep_counter:02d} -> {special_name}')
            shutil.copy2(str(video), str(output_dir / special_name))
            ep_counter += 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Split double-episode files and renumber sequentially per season.',
    )
    parser.add_argument(
        'season_dirs', nargs='+', type=Path,
        help='Season directory/directories to process',
    )
    parser.add_argument(
        '--output-dir', '-o', type=Path, required=True,
        help='Root output directory (S01/S02/... subdirs created automatically)',
    )
    parser.add_argument(
        '--threshold', type=float, default=0.5,
        help='TransNetV2 scene detection threshold (default: 0.5)',
    )
    parser.add_argument(
        '--min-scene-len', type=int, default=10,
        help='Minimum scene length in frames (default: 10)',
    )
    parser.add_argument(
        '--black-window', type=float, default=15.0,
        help='Half-window in seconds for symmetric black frame scan (default: 15)',
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Classify only — no TransNetV2, no splitting, no copying',
    )

    args = parser.parse_args()

    for season_dir in args.season_dirs:
        if not season_dir.is_dir():
            print(f'Not a directory, skipping: {season_dir}', file=sys.stderr)
            continue
        _process_season(
            season_dir,
            args.output_dir / season_dir.name,
            args.black_window,
            args.threshold,
            args.min_scene_len,
            args.dry_run,
        )


if __name__ == '__main__':
    main()

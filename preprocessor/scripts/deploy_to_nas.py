import argparse
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)
from pathlib import Path
import shutil
import sys
from typing import (
    List,
    Tuple,
)

_DEPLOY_SUBDIRS = ("archives", "transcoded_videos")
_DEFAULT_WORKERS = 8


def _resolve_source_base(source_path: str) -> Path:
    if source_path:
        return Path(source_path)
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent / "output_data"


def _collect_files(source_series_dir: Path, target_series_dir: Path) -> List[Tuple[Path, Path]]:
    pairs = []
    for subdir in _DEPLOY_SUBDIRS:
        source_subdir = source_series_dir / subdir
        if not source_subdir.exists():
            print(f"  [SKIP] Source not found: {source_subdir}")
            continue
        for source_file in source_subdir.rglob("*"):
            if source_file.is_file():
                relative = source_file.relative_to(source_subdir)
                target_file = target_series_dir / relative
                pairs.append((source_file, target_file))
    return pairs


def _copy_file(src: Path, dst: Path, dry_run: bool) -> Tuple[Path, Path, bool, str]:
    try:
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return src, dst, True, ""
    except Exception as e:
        return src, dst, False, str(e)


def _print_summary(total: int, copied: int, skipped: int, failed: int, dry_run: bool) -> None:
    prefix = "[DRY RUN] " if dry_run else ""
    print(f"\n{prefix}Summary:")
    print(f"  Total files : {total}")
    print(f"  Copied      : {copied}")
    print(f"  Skipped     : {skipped}")
    print(f"  Failed      : {failed}")


def _filter_files_to_copy(
    pairs: List[Tuple[Path, Path]], overwrite: bool,
) -> Tuple[List[Tuple[Path, Path]], int]:
    to_copy = []
    skipped = 0
    for src, dst in pairs:
        if not overwrite and dst.exists():
            skipped += 1
        else:
            to_copy.append((src, dst))
    return to_copy, skipped


def _execute_copy_batch(
    to_copy: List[Tuple[Path, Path]],
    target_series_dir: Path,
    dry_run: bool,
    workers: int,
) -> Tuple[int, int]:
    copied = 0
    failed = 0
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_copy_file, src, dst, dry_run): src for src, dst in to_copy}
        for future in as_completed(futures):
            src, result_dst, success, error = future.result()
            done += 1
            if success:
                copied += 1
                rel = result_dst.relative_to(target_series_dir)
                print(f"  [{'DRY' if dry_run else 'OK'}] {rel}  ({done}/{len(to_copy)})")
            else:
                failed += 1
                print(f"  [FAIL] {src.name} — {error}")
    return copied, failed


def deploy(
    source_base: Path,
    target_base: Path,
    series: str,
    dry_run: bool,
    workers: int,
    overwrite: bool,
) -> int:
    source_series_dir = source_base / series
    target_series_dir = target_base / series

    if not source_series_dir.exists():
        print(f"ERROR: Source directory not found: {source_series_dir}")
        return 1

    print(f"Source : {source_series_dir}")
    print(f"Target : {target_series_dir}")
    print(f"Mode   : {'DRY RUN' if dry_run else 'COPY'} | workers={workers} | overwrite={overwrite}")
    print()

    pairs = _collect_files(source_series_dir, target_series_dir)
    if not pairs:
        print("No files found to copy.")
        return 0

    to_copy, skipped = _filter_files_to_copy(pairs, overwrite)
    print(f"Files to copy : {len(to_copy)}")
    print(f"Files skipped : {skipped} (already exist, use --overwrite to replace)")
    print()

    if not to_copy:
        _print_summary(len(pairs), 0, skipped, 0, dry_run)
        return 0

    copied, failed = _execute_copy_batch(to_copy, target_series_dir, dry_run, workers)
    _print_summary(len(pairs), copied, skipped, failed, dry_run)
    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copy processed series archives and videos to NAS storage.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example:\n  python -m preprocessor.scripts.deploy_to_nas"
               " --target-path //TRUENAS/RanchBot --series kiepscy",
    )
    parser.add_argument(
        "--target-path",
        required=True,
        help="Base NAS path (e.g. //TRUENAS/RanchBot or /mnt/truenas/RanchBot)",
    )
    parser.add_argument(
        "--series",
        required=True,
        help="Series name (e.g. kiepscy, ranczo)",
    )
    parser.add_argument(
        "--source-path",
        default="",
        help="Override local output_data base path (default: auto-detected relative to this script)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite files that already exist on target",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be copied without actually copying",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=_DEFAULT_WORKERS,
        help=f"Number of parallel copy workers (default: {_DEFAULT_WORKERS})",
    )

    args = parser.parse_args()

    source_base = _resolve_source_base(args.source_path)
    target_base = Path(args.target_path)

    sys.exit(deploy(source_base, target_base, args.series, args.dry_run, args.workers, args.overwrite))


if __name__ == "__main__":
    main()

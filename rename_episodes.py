#!/usr/bin/env python3
import re
from pathlib import Path
from typing import Dict, List, Tuple


def _extract_episode_number(filename: str) -> int:
    match = re.search(r'\.E(\d+)\.', filename)
    if not match:
        raise ValueError(f"Cannot extract episode number from: {filename}")
    return int(match.group(1))


def _build_mapping() -> Dict[int, Tuple[int, int, int]]:
    season_ranges = [
        (1, 1, 145),
        (2, 146, 154),
        (3, 155, 171),
        (4, 172, 202),
        (5, 203, 244),
        (6, 245, 265),
        (7, 266, 282),
        (8, 283, 297),
        (9, 298, 310),
        (10, 311, 322),
        (11, 323, 337),
        (12, 338, 352),
        (13, 353, 365),
        (14, 366, 379),
        (15, 380, 392),
        (16, 393, 405),
        (17, 406, 418),
        (18, 419, 431),
        (19, 432, 444),
        (20, 445, 456),
        (21, 457, 468),
        (22, 469, 480),
        (23, 481, 492),
        (24, 493, 504),
        (25, 505, 516),
        (26, 517, 528),
        (27, 529, 540),
        (28, 541, 552),
        (29, 553, 564),
        (30, 565, 576),
        (31, 577, 589),
    ]

    absolute_to_relative = {}
    for season_num, start_ep, end_ep in season_ranges:
        for absolute_ep in range(start_ep, end_ep + 1):
            relative_ep = absolute_ep - start_ep + 1
            absolute_to_relative[absolute_ep] = (season_num, relative_ep, absolute_ep)

    return absolute_to_relative


def _rename_files_in_season(
    season_dir: Path,
    season_num: int,
    mapping: Dict[int, Tuple[int, int, int]],
    dry_run: bool = True
) -> List[str]:
    changes = []

    if not season_dir.exists():
        return changes

    files = sorted(season_dir.glob("*.mp4"))

    for file_path in files:
        old_name = file_path.name

        try:
            absolute_ep = _extract_episode_number(old_name)
        except ValueError as e:
            changes.append(f"⚠️  SKIP: {old_name} - {e}")
            continue

        if absolute_ep not in mapping:
            changes.append(f"⚠️  SKIP: {old_name} - episode {absolute_ep} not in mapping")
            continue

        mapped_season, relative_ep, _ = mapping[absolute_ep]

        if mapped_season != season_num:
            changes.append(
                f"❌ ERROR: {old_name} - episode E{absolute_ep} should be in season {mapped_season}, not {season_num}"
            )
            continue

        new_name = re.sub(
            r'ŚwiatWedługKiepskich\.E\d+\.',
            f'S{season_num:02d}E{relative_ep:03d}.',
            old_name
        )

        if new_name == old_name:
            changes.append(f"⚠️  UNCHANGED: {old_name}")
            continue

        new_path = file_path.parent / new_name

        if new_path.exists() and new_path != file_path:
            changes.append(f"❌ ERROR: {old_name} -> {new_name} - target file already exists!")
            continue

        changes.append(f"✓ {old_name}\n    → {new_name}")

        if not dry_run:
            file_path.rename(new_path)

    return changes


def _rename_season_folders(input_data_dir: Path, dry_run: bool = True) -> List[str]:
    changes = []

    season_folders = sorted(input_data_dir.glob("Season_*"))

    for old_folder in season_folders:
        match = re.match(r'Season_(\d+)', old_folder.name)
        if not match:
            changes.append(f"⚠️  SKIP folder: {old_folder.name} - doesn't match Season_## pattern")
            continue

        season_num = int(match.group(1))
        new_folder_name = f"S{season_num:02d}"
        new_folder_path = old_folder.parent / new_folder_name

        if new_folder_path.exists() and new_folder_path != old_folder:
            changes.append(f"❌ ERROR: {old_folder.name} -> {new_folder_name} - target folder already exists!")
            continue

        changes.append(f"📁 {old_folder.name} → {new_folder_name}")

        if not dry_run:
            old_folder.rename(new_folder_path)

    return changes


def main() -> None:
    input_data_dir = Path("/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/input_data")

    if not input_data_dir.exists():
        print(f"❌ Directory not found: {input_data_dir}")
        return

    print("=" * 80)
    print("EPISODE RENAMING SCRIPT - DRY RUN")
    print("=" * 80)
    print()

    mapping = _build_mapping()

    print("STEP 1: Rename files in each season folder")
    print("-" * 80)

    all_file_changes = []
    for season_num in range(1, 32):
        season_folder = input_data_dir / f"Season_{season_num:02d}"
        if not season_folder.exists():
            continue

        print(f"\n📂 Season_{season_num:02d}:")
        changes = _rename_files_in_season(season_folder, season_num, mapping, dry_run=True)

        if changes:
            for change in changes[:5]:
                print(f"  {change}")
            if len(changes) > 5:
                print(f"  ... and {len(changes) - 5} more files")
            all_file_changes.extend(changes)
        else:
            print("  (no files to rename)")

    print()
    print("=" * 80)
    print("STEP 2: Rename season folders")
    print("-" * 80)

    folder_changes = _rename_season_folders(input_data_dir, dry_run=True)
    for change in folder_changes:
        print(f"  {change}")

    print()
    print("=" * 80)
    print("SUMMARY")
    print("-" * 80)
    print(f"Total files to rename: {len([c for c in all_file_changes if c.startswith('✓')])}")
    print(f"Total folders to rename: {len([c for c in folder_changes if c.startswith('📁')])}")
    print(f"Errors: {len([c for c in all_file_changes + folder_changes if '❌' in c])}")
    print()
    print("This was a DRY RUN. No files were actually renamed.")
    print()

    response = input("Do you want to proceed with the actual renaming? (yes/no): ").strip().lower()

    if response == "yes":
        print()
        print("=" * 80)
        print("EXECUTING RENAME OPERATIONS")
        print("=" * 80)

        print("\nRenaming files...")
        for season_num in range(1, 32):
            season_folder = input_data_dir / f"Season_{season_num:02d}"
            if season_folder.exists():
                _rename_files_in_season(season_folder, season_num, mapping, dry_run=False)

        print("\nRenaming folders...")
        _rename_season_folders(input_data_dir, dry_run=False)

        print()
        print("✅ DONE! All files and folders have been renamed.")
    else:
        print("Operation cancelled.")


if __name__ == "__main__":
    main()

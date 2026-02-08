import json
from pathlib import Path
import re
import shutil
from typing import (
    Optional,
    Tuple,
)

SOURCE_DIR = Path("/mnt/c/GIT_REPO/RANCZO_KLIPY/sceny-trans")
OUTPUT_DIR = Path("/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/output_data/transcriptions")
SERIES_NAME = "ranczo"


def parse_filename(filename: str) -> Optional[Tuple[int, int]]:
    match = re.search(r"S(\d{2})E(\d{2})", filename, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


def _copy_and_fix_file(source_dir: Path, filename_base: str, season: int, episode: int) -> bool:
    raw_dir = OUTPUT_DIR / f"S{season:02d}" / f"E{episode:02d}" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    episode_info = {
        "season": season,
        "episode_number": episode,
    }

    segmented_src = source_dir / "segmented_json" / f"{filename_base}_segmented.json"
    simple_src = source_dir / "simple_json" / f"{filename_base}_simple.json"
    srt_src = source_dir / "srt" / f"{filename_base}.srt"
    txt_src = source_dir / "txt" / f"{filename_base}.txt"

    if not segmented_src.exists():
        print(f"  ERROR: Missing {segmented_src.name}")
        return False

    try: # pylint: disable=too-many-try-statements
        with open(segmented_src, "r", encoding="utf-8") as f:
            segmented_data = json.load(f)
        segmented_data["episode_info"] = episode_info
        segmented_dst = raw_dir / f"{SERIES_NAME}_S{season:02d}E{episode:02d}_segmented.json"
        with open(segmented_dst, "w", encoding="utf-8") as f:
            json.dump(segmented_data, f, indent=2, ensure_ascii=False)
        print(f"  Created: {segmented_dst}")

        with open(simple_src, "r", encoding="utf-8") as f:
            simple_data = json.load(f)
        simple_data["episode_info"] = episode_info
        simple_dst = raw_dir / f"{SERIES_NAME}_S{season:02d}E{episode:02d}_simple.json"
        with open(simple_dst, "w", encoding="utf-8") as f:
            json.dump(simple_data, f, indent=2, ensure_ascii=False)
        print(f"  Created: {simple_dst}")

        srt_dst = raw_dir / f"{SERIES_NAME}_S{season:02d}E{episode:02d}.srt"
        shutil.copy2(srt_src, srt_dst)
        print(f"  Created: {srt_dst}")

        txt_dst = raw_dir / f"{SERIES_NAME}_S{season:02d}E{episode:02d}.txt"
        shutil.copy2(txt_src, txt_dst)
        print(f"  Created: {txt_dst}")

        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def main() -> None:
    print(f"Source: {SOURCE_DIR}")
    print(f"Output: {OUTPUT_DIR}")

    segmented_dir = SOURCE_DIR / "segmented_json"
    if not segmented_dir.exists():
        print(f"ERROR: {segmented_dir} does not exist")
        return

    for segmented_file in sorted(segmented_dir.glob("*_segmented.json")):
        filename_base = segmented_file.stem.replace("_segmented", "")

        parsed = parse_filename(filename_base)
        if not parsed:
            print(f"Skipping (cannot parse): {filename_base}")
            continue

        season, episode = parsed
        print(f"{filename_base} -> S{season:02d}E{episode:02d}")
        _copy_and_fix_file(SOURCE_DIR, filename_base, season, episode)


if __name__ == "__main__":
    main()

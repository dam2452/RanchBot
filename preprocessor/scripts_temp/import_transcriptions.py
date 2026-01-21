from __future__ import annotations

import json
from pathlib import Path
import re

SOURCE_DIR = Path("/mnt/c/Users/dam2452/Downloads/output_ranczo/json")
OUTPUT_DIR = Path("/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/output_data/transcriptions")
SERIES_NAME = "ranczo"


def parse_filename(filename: str) -> tuple[int, int] | None:
    match = re.search(r"S(\d{2})E(\d{2})", filename, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


def convert_file(source_file: Path, season: int, episode: int) -> bool:
    episode_dir = OUTPUT_DIR / f"S{season:02d}" / f"E{episode:02d}"
    episode_dir.mkdir(parents=True, exist_ok=True)

    try:
        with open(source_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"  ERROR: Invalid JSON in {source_file.name}: {e}")
        return False

    if not data:
        print(f"  ERROR: Empty file {source_file.name}")
        return False

    episode_info = {
        "season": season,
        "episode_number": episode,
    }

    full_json = {
        "episode_info": episode_info,
        "language_code": data.get("language_code", "pol"),
        "language_probability": data.get("language_probability", 1.0),
        "text": data.get("text", ""),
        "words": data.get("words", []),
    }

    output_filename = f"{SERIES_NAME}_S{season:02d}E{episode:02d}.json"
    output_file = episode_dir / output_filename
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(full_json, f, indent=2, ensure_ascii=False)
    print(f"Created: {output_file}")

    generate_segmented(data, episode_dir, season, episode, episode_info)
    generate_simple(data, episode_dir, season, episode, episode_info)
    generate_srt(data, episode_dir, season, episode)
    generate_txt(data, episode_dir, season, episode)
    return True


def generate_segmented(data: dict, episode_dir: Path, season: int, episode: int, episode_info: dict) -> None:
    words = data.get("words", [])
    segments = []
    current_segment = {"text": "", "words": []}

    for word in words:
        word_text = word.get("text", "")
        current_segment["words"].append(word)
        current_segment["text"] += word_text + " "

        if word_text.endswith((".", "?", "!", ")")):
            current_segment["text"] = current_segment["text"].strip()
            if current_segment["text"]:
                segments.append(current_segment)
            current_segment = {"text": "", "words": []}

    if current_segment["text"].strip():
        current_segment["text"] = current_segment["text"].strip()
        segments.append(current_segment)

    segmented_json = {
        "episode_info": episode_info,
        "segments": segments,
    }

    output_filename = f"{SERIES_NAME}_S{season:02d}E{episode:02d}_segmented.json"
    output_file = episode_dir / output_filename
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(segmented_json, f, indent=2, ensure_ascii=False)
    print(f"Created: {output_file}")


def generate_simple(data: dict, episode_dir: Path, season: int, episode: int, episode_info: dict) -> None:
    words = data.get("words", [])
    segments = []
    current_segment = {"speaker": "speaker_unknown", "text": ""}

    for word in words:
        word_text = word.get("text", "")
        speaker = word.get("speaker_id", "speaker_unknown")

        if current_segment["speaker"] != speaker and current_segment["text"]:
            current_segment["text"] = current_segment["text"].strip()
            segments.append(current_segment)
            current_segment = {"speaker": speaker, "text": ""}

        current_segment["speaker"] = speaker
        current_segment["text"] += word_text + " "

    if current_segment["text"].strip():
        current_segment["text"] = current_segment["text"].strip()
        segments.append(current_segment)

    simple_json = {
        "episode_info": episode_info,
        "segments": segments,
    }

    output_filename = f"{SERIES_NAME}_S{season:02d}E{episode:02d}_simple.json"
    output_file = episode_dir / output_filename
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(simple_json, f, indent=2, ensure_ascii=False)
    print(f"Created: {output_file}")


def format_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(data: dict, episode_dir: Path, season: int, episode: int) -> None:
    words = data.get("words", [])
    srt_lines = []
    index = 1

    segment_words = []
    segment_text = ""

    for word in words:
        word_text = word.get("text", "")
        segment_words.append(word)
        segment_text += word_text + " "

        if word_text.endswith((".", "?", "!", ")")):
            if segment_words and segment_text.strip():
                start = segment_words[0].get("start", 0.0)
                end = segment_words[-1].get("end", 0.0)
                text = segment_text.strip()

                srt_lines.append(f"{index}")
                srt_lines.append(f"{format_timestamp(start)} --> {format_timestamp(end)}")
                srt_lines.append(text)
                srt_lines.append("")
                index += 1

            segment_words = []
            segment_text = ""

    if segment_words and segment_text.strip():
        start = segment_words[0].get("start", 0.0)
        end = segment_words[-1].get("end", 0.0)
        text = segment_text.strip()
        srt_lines.append(f"{index}")
        srt_lines.append(f"{format_timestamp(start)} --> {format_timestamp(end)}")
        srt_lines.append(text)
        srt_lines.append("")

    output_filename = f"{SERIES_NAME}_S{season:02d}E{episode:02d}.srt"
    output_file = episode_dir / output_filename
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))
    print(f"Created: {output_file}")


def generate_txt(data: dict, episode_dir: Path, season: int, episode: int) -> None:
    text = data.get("text", "")

    output_filename = f"{SERIES_NAME}_S{season:02d}E{episode:02d}.txt"
    output_file = episode_dir / output_filename
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Created: {output_file}")


def main() -> None:
    print(f"Source: {SOURCE_DIR}")
    print(f"Output: {OUTPUT_DIR}")

    for season_dir in sorted(SOURCE_DIR.iterdir()):
        if not season_dir.is_dir():
            continue

        print(f"\nProcessing: {season_dir.name}")

        if "Ranczo Wilkowyje" in season_dir.name:
            for json_file in sorted(season_dir.glob("*.json")):
                print(f"  {json_file.name} -> S00E01 (special)")
                convert_file(json_file, 0, 1)
            continue

        for json_file in sorted(season_dir.glob("*.json")):
            parsed = parse_filename(json_file.name)
            if not parsed:
                print(f"  Skipping (cannot parse): {json_file.name}")
                continue

            season, episode = parsed
            print(f"  {json_file.name} -> S{season:02d}E{episode:02d}")
            convert_file(json_file, season, episode)


if __name__ == "__main__":
    main()

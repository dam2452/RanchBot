import json
from pathlib import Path
import re
from typing import (
    Any,
    Dict,
    List,
    Tuple,
)

from preprocessor.config.config import settings
from preprocessor.core.base_processor import (
    BaseProcessor,
    OutputSpec,
    ProcessingItem,
)
from preprocessor.core.constants import (
    FILE_EXTENSIONS,
    FILE_SUFFIXES,
)
from preprocessor.core.episode_manager import EpisodeManager


class SoundEventSeparator(BaseProcessor):

    def __init__(self, args: Dict[str, Any]) -> None:
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=2,
            loglevel=args.get("loglevel", 20),
        )

        self.transcription_dir = Path(self._args.get("transcription_dir", settings.transcription.output_dir))
        episodes_info_json = self._args.get("episodes_info_json")
        self.episode_manager = EpisodeManager(episodes_info_json, self.series_name)

    def _validate_args(self, args: Dict[str, Any]) -> None:
        pass

    def _get_processing_items(self) -> List[ProcessingItem]:
        segmented_files = list(self.transcription_dir.rglob("**/raw/*_segmented.json"))

        items = []
        for trans_file in segmented_files:
            episode_info = self.episode_manager.parse_filename(trans_file)
            if not episode_info:
                self.logger.warning(f"Cannot parse episode info from {trans_file.name}")
                continue

            episode_id = EpisodeManager.get_episode_id_for_state(episode_info)

            items.append(
                ProcessingItem(
                    episode_id=episode_id,
                    input_path=trans_file,
                    metadata={"episode_info": episode_info},
                ),
            )

        return items

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        base_name = item.input_path.stem.replace(FILE_SUFFIXES["segmented"], "")
        episode_dir = item.input_path.parent.parent
        clean_dir = episode_dir / settings.output_subdirs.transcription_subdirs.clean
        sound_dir = episode_dir / settings.output_subdirs.transcription_subdirs.sound_events

        clean_json = clean_dir / f"{base_name}{FILE_SUFFIXES['clean']}{FILE_EXTENSIONS['json']}"
        sound_json = sound_dir / f"{base_name}{FILE_SUFFIXES['sound_events']}{FILE_EXTENSIONS['json']}"
        clean_segmented_json = clean_dir / f"{base_name}{FILE_SUFFIXES['segmented']}_clean{FILE_EXTENSIONS['json']}"
        sound_segmented_json = sound_dir / f"{base_name}{FILE_SUFFIXES['segmented']}_sound_events{FILE_EXTENSIONS['json']}"
        clean_txt = clean_dir / f"{base_name}{FILE_SUFFIXES['clean']}{FILE_EXTENSIONS['txt']}"
        sound_txt = sound_dir / f"{base_name}{FILE_SUFFIXES['sound_events']}{FILE_EXTENSIONS['txt']}"
        clean_srt = clean_dir / f"{base_name}{FILE_SUFFIXES['clean']}{FILE_EXTENSIONS['srt']}"
        sound_srt = sound_dir / f"{base_name}{FILE_SUFFIXES['sound_events']}{FILE_EXTENSIONS['srt']}"

        return [
            OutputSpec(path=clean_json, required=True),
            OutputSpec(path=sound_json, required=True),
            OutputSpec(path=clean_segmented_json, required=True),
            OutputSpec(path=sound_segmented_json, required=True),
            OutputSpec(path=clean_txt, required=True),
            OutputSpec(path=sound_txt, required=True),
            OutputSpec(path=clean_srt, required=True),
            OutputSpec(path=sound_srt, required=True),
        ]

    def _process_item(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> None:  # pylint: disable=too-many-locals
        with open(item.input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        episode_info = data.get("episode_info", {})
        segments = data.get("segments", [])

        dialogue_segments = []
        sound_event_segments = []

        for segment in segments:
            classification = self.__classify_segment(segment)

            if classification == "dialogue":
                dialogue_segments.append(self.__clean_segment_text(segment))
            elif classification == "sound_event":
                sound_event_segments.append(self.__enrich_sound_event(self.__clean_segment_text(segment)))
            elif classification == "mixed":
                dialogue_parts, sound_parts = self.__split_mixed_segment(segment)
                dialogue_segments.extend(dialogue_parts)
                sound_event_segments.extend([self.__enrich_sound_event(s) for s in sound_parts])

        dialogue_segments = self.__renumber_segments(dialogue_segments)
        sound_event_segments = self.__renumber_segments(sound_event_segments)

        base_name = item.input_path.stem.replace(FILE_SUFFIXES["segmented"], "")
        episode_dir = item.input_path.parent.parent
        clean_dir = episode_dir / settings.output_subdirs.transcription_subdirs.clean
        sound_dir = episode_dir / settings.output_subdirs.transcription_subdirs.sound_events

        clean_dir.mkdir(parents=True, exist_ok=True)
        sound_dir.mkdir(parents=True, exist_ok=True)

        clean_json = clean_dir / f"{base_name}_clean_transcription.json"
        sound_json = sound_dir / f"{base_name}_sound_events.json"
        clean_segmented_json = clean_dir / f"{base_name}_segmented_clean.json"
        sound_segmented_json = sound_dir / f"{base_name}_segmented_sound_events.json"
        clean_txt = clean_dir / f"{base_name}_clean_transcription.txt"
        sound_txt = sound_dir / f"{base_name}_sound_events.txt"
        clean_srt = clean_dir / f"{base_name}_clean_transcription.srt"
        sound_srt = sound_dir / f"{base_name}_sound_events.srt"

        raw_txt = episode_dir / settings.output_subdirs.transcription_subdirs.raw / f"{base_name}.txt"

        dialogue_segments_simple = self.__convert_to_simple_format(dialogue_segments)
        sound_event_segments_simple = self.__convert_to_simple_format(sound_event_segments)

        with open(clean_json, "w", encoding="utf-8") as f:
            json.dump(
                {"episode_info": episode_info, "segments": dialogue_segments_simple},
                f,
                ensure_ascii=False,
                indent=4,
            )

        with open(sound_json, "w", encoding="utf-8") as f:
            json.dump(
                {"episode_info": episode_info, "segments": sound_event_segments_simple},
                f,
                ensure_ascii=False,
                indent=4,
            )

        with open(clean_segmented_json, "w", encoding="utf-8") as f:
            json.dump(
                {"episode_info": episode_info, "segments": dialogue_segments},
                f,
                ensure_ascii=False,
                indent=4,
            )

        with open(sound_segmented_json, "w", encoding="utf-8") as f:
            json.dump(
                {"episode_info": episode_info, "segments": sound_event_segments},
                f,
                ensure_ascii=False,
                indent=4,
            )

        self.__generate_txt_files(raw_txt, clean_txt, sound_txt)
        self.__generate_srt_files(dialogue_segments, sound_event_segments, clean_srt, sound_srt)

        self.logger.info(
            f"Separated {item.episode_id}: "
            f"{len(dialogue_segments)} dialogue, {len(sound_event_segments)} sound events",
        )

    def __classify_segment(self, segment: Dict) -> str:
        words = segment.get("words", [])
        if not words:
            return "dialogue"

        has_sound = False
        has_dialogue = False

        for word in words:
            if self.__is_sound_event(word):
                has_sound = True
            elif word.get("type") not in ["spacing", ""]:
                has_dialogue = True

        if has_sound and has_dialogue:
            return "mixed"
        if has_sound:
            return "sound_event"
        return "dialogue"

    def __is_sound_event(self, word: Dict) -> bool:
        if word.get("type") == "audio_event":
            return True

        text = word.get("text", "").strip()
        if re.match(r'^\(.*\)$', text):
            return True

        return False

    def __split_mixed_segment(self, segment: Dict) -> Tuple[List[Dict], List[Dict]]:
        words = segment.get("words", [])
        dialogue_sequences = []
        sound_sequences = []

        current_type = None
        current_words = []

        for word in words:
            if word.get("type") == "spacing":
                if current_words:
                    current_words.append(word)
                continue

            is_sound = self.__is_sound_event(word)
            word_type = "sound" if is_sound else "dialogue"

            if word_type != current_type:
                if current_words:
                    self.__finalize_sequence(
                        current_type, current_words, dialogue_sequences, sound_sequences, segment,
                    )
                current_type = word_type
                current_words = [word]
            else:
                current_words.append(word)

        if current_words:
            self.__finalize_sequence(
                current_type, current_words, dialogue_sequences, sound_sequences, segment,
            )

        return dialogue_sequences, sound_sequences

    def __finalize_sequence(
        self,
        seq_type: str,
        words: List[Dict],
        dialogue_sequences: List[Dict],
        sound_sequences: List[Dict],
        original_segment: Dict,
    ) -> None:
        if not words:
            return

        non_spacing_words = [w for w in words if w.get("type") != "spacing"]
        if not non_spacing_words:
            return

        text = "".join([w.get("text", "") for w in words])
        text = re.sub(r'\s+', ' ', text).strip()
        start_time = min((w.get("start") or 0) for w in words)
        end_time = max((w.get("end") or 0) for w in words)

        new_segment = {
            "text": text,
            "start": start_time,
            "end": end_time,
            "words": words,
        }

        for key in original_segment:
            if key not in ["text", "start", "end", "words"]:
                new_segment[key] = original_segment[key]

        if seq_type == "dialogue":
            dialogue_sequences.append(new_segment)
        else:
            sound_sequences.append(new_segment)

    def __clean_segment_text(self, segment: Dict) -> Dict:
        cleaned = segment.copy()
        if "text" in cleaned:
            text = cleaned["text"]
            text = re.sub(r'\s+', ' ', text).strip()
            cleaned["text"] = text

        if cleaned.get("start") is None or cleaned.get("end") is None:
            words = cleaned.get("words", [])
            if words:
                starts = [(w.get("start") or 0) for w in words if w.get("start") is not None]
                ends = [(w.get("end") or 0) for w in words if w.get("end") is not None]
                if starts:
                    cleaned["start"] = min(starts)
                if ends:
                    cleaned["end"] = max(ends)

        return cleaned

    def __enrich_sound_event(self, segment: Dict) -> Dict:
        enriched = segment.copy()
        enriched["sound_type"] = "sound"
        return enriched

    @staticmethod
    def __renumber_segments(segments: List[Dict]) -> List[Dict]:
        for i, segment in enumerate(segments):
            segment["id"] = i
        return segments

    @staticmethod
    def __convert_to_simple_format(segments: List[Dict]) -> List[Dict]:
        simple_segments = []
        for seg in segments:
            simple_seg = {
                "id": seg.get("id"),
                "text": seg.get("text", ""),
                "start": seg.get("start") or 0.0,
                "end": seg.get("end") or 0.0,
            }
            if "sound_type" in seg:
                simple_seg["sound_type"] = seg["sound_type"]
            simple_segments.append(simple_seg)
        return simple_segments

    def __generate_txt_files(self, original_txt: Path, clean_txt: Path, sound_txt: Path) -> None:
        if not original_txt.exists():
            self.logger.warning(f"Original TXT file not found: {original_txt}")
            return

        with open(original_txt, "r", encoding="utf-8") as f:
            original_content = f.read()

        clean_content = re.sub(r'\([^)]*\)', '', original_content)
        clean_content = re.sub(r'\s+', ' ', clean_content).strip()

        sound_matches = re.findall(r'\([^)]*\)', original_content)
        sound_content = ' '.join(sound_matches)

        with open(clean_txt, "w", encoding="utf-8") as f:
            f.write(clean_content)

        with open(sound_txt, "w", encoding="utf-8") as f:
            f.write(sound_content)

    @staticmethod
    def __generate_srt_files(
        dialogue_segments: List[Dict],
        sound_segments: List[Dict],
        clean_srt: Path,
        sound_srt: Path,
    ) -> None:
        def format_timestamp(seconds: float) -> str:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int((seconds % 1) * 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

        def write_srt(segments: List[Dict], output_path: Path) -> None:
            with open(output_path, "w", encoding="utf-8") as f:
                for idx, seg in enumerate(segments, start=1):
                    words = seg.get("words", [])
                    text = seg.get("text", "").strip()

                    if not text or not words:
                        continue

                    non_spacing_words = [w for w in words if w.get("type") != "spacing"]
                    if not non_spacing_words:
                        continue

                    start_time = min((w.get("start") or 0.0) for w in non_spacing_words)
                    end_time = max((w.get("end") or 0.0) for w in non_spacing_words)

                    f.write(f"{idx}\n")
                    f.write(f"{format_timestamp(start_time)} --> {format_timestamp(end_time)}\n")
                    f.write(f"{text}\n\n")

        write_srt(dialogue_segments, clean_srt)
        write_srt(sound_segments, sound_srt)

    def _get_progress_description(self) -> str:
        return "Separating sound events from dialogues"

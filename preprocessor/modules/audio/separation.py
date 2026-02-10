import json
from pathlib import Path
import re
from typing import (
    Any,
    Dict,
    List,
    Tuple,
)

from preprocessor.config.constants import (
    FILE_EXTENSIONS,
    FILE_SUFFIXES,
)
from preprocessor.config.step_configs import SoundSeparationConfig
from preprocessor.config.types import (
    WordKeys,
    WordTypeValues,
)
from preprocessor.core.artifacts import TranscriptionData
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.lib.io.files import atomic_write_json
from preprocessor.lib.transcription.sound_classification import (
    classify_segment,
    is_sound_event,
)


class SoundSeparationStep(PipelineStep[TranscriptionData, TranscriptionData, SoundSeparationConfig]):

    @property
    def name(self) -> str:
        return 'sound_separation'

    def execute(  # pylint: disable=too-many-locals
        self,
        input_data: TranscriptionData,
        context: ExecutionContext,
    ) -> TranscriptionData:
        base_name = input_data.path.stem.replace(FILE_SUFFIXES['segmented'], '')
        episode_dir = input_data.path.parent.parent
        clean_dir = episode_dir / 'clean'
        sound_dir = episode_dir / 'sound_events'
        clean_dir.mkdir(parents=True, exist_ok=True)
        sound_dir.mkdir(parents=True, exist_ok=True)
        clean_json = (
            clean_dir /
            f"{base_name}{FILE_SUFFIXES['clean']}{FILE_EXTENSIONS['json']}"
        )
        sound_json = (
            sound_dir /
            f"{base_name}{FILE_SUFFIXES['sound_events']}{FILE_EXTENSIONS['json']}"
        )
        if clean_json.exists() and sound_json.exists() and (not context.force_rerun):
            if context.is_step_completed(self.name, input_data.episode_id):
                context.logger.info(f'Skipping {input_data.episode_id} (cached)')
                return TranscriptionData(
                    path=clean_json,
                    episode_id=input_data.episode_id,
                    episode_info=input_data.episode_info,
                    language=input_data.language,
                    model=input_data.model,
                    format='json',
                )
        context.mark_step_started(self.name, input_data.episode_id)
        with open(input_data.path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        episode_info_dict = data.get('episode_info', {})
        segments = data.get('segments', [])
        dialogue_segments = []
        sound_segments = []
        for segment in segments:
            classification = classify_segment(segment)
            if classification == 'dialogue':
                cleaned = self._clean_segment_text(segment)
                dialogue_segments.append(cleaned)
            elif classification == 'sound_event':
                cleaned = self._clean_segment_text(segment)
                cleaned['sound_type'] = 'sound'
                sound_segments.append(cleaned)
            elif classification == 'mixed':
                dialogue_parts, sound_parts = self._split_mixed_segment(segment)
                dialogue_segments.extend(dialogue_parts)
                sound_segments.extend(sound_parts)
        dialogue_segments = self._renumber_segments(dialogue_segments)
        sound_segments = self._renumber_segments(sound_segments)
        clean_data = {'episode_info': episode_info_dict, 'segments': dialogue_segments}
        sound_data = {'episode_info': episode_info_dict, 'segments': sound_segments}
        atomic_write_json(clean_json, clean_data)
        atomic_write_json(sound_json, sound_data)
        clean_segmented = (
            clean_dir /
            f"{base_name}{FILE_SUFFIXES['segmented']}_clean{FILE_EXTENSIONS['json']}"
        )
        sound_segmented = (
            sound_dir /
            f"{base_name}{FILE_SUFFIXES['segmented']}_sound_events{FILE_EXTENSIONS['json']}"
        )
        atomic_write_json(clean_segmented, clean_data)
        atomic_write_json(sound_segmented, sound_data)
        clean_txt = clean_dir / f"{base_name}{FILE_SUFFIXES['clean']}{FILE_EXTENSIONS['txt']}"
        sound_txt = sound_dir / f"{base_name}{FILE_SUFFIXES['sound_events']}{FILE_EXTENSIONS['txt']}"
        clean_srt = clean_dir / f"{base_name}{FILE_SUFFIXES['clean']}{FILE_EXTENSIONS['srt']}"
        sound_srt = sound_dir / f"{base_name}{FILE_SUFFIXES['sound_events']}{FILE_EXTENSIONS['srt']}"
        self._generate_txt_file(clean_json, clean_txt)
        self._generate_txt_file(sound_json, sound_txt)
        self._generate_srt_file(dialogue_segments, clean_srt)
        self._generate_srt_file(sound_segments, sound_srt)
        context.mark_step_completed(self.name, input_data.episode_id)
        return TranscriptionData(
            path=clean_json,
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            language=input_data.language,
            model=input_data.model,
            format='json',
        )

    @staticmethod
    def _is_sound_event_text(text: str) -> bool:
        return bool(re.match(r'^\(.*\)$', text.strip()))

    def _split_mixed_segment(
        self,
        segment: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        words = segment.get(WordKeys.WORDS, [])
        dialogue_parts = []
        sound_parts = []
        current_type = None
        current_words = []
        current_start = None
        for word in words:
            word_type = 'sound' if is_sound_event(word) else 'dialogue'
            if word.get(WordKeys.TYPE) == WordTypeValues.SPACING:
                if current_words:
                    current_words.append(word)
                continue
            if word_type != current_type:
                if current_words and current_type:
                    self._finalize_sequence(
                        current_type,
                        current_words,
                        current_start,
                        dialogue_parts,
                        sound_parts,
                    )
                current_type = word_type
                current_words = [word]
                current_start = word.get(WordKeys.START)
            else:
                current_words.append(word)
        if current_words and current_type:
            self._finalize_sequence(
                current_type,
                current_words,
                current_start,
                dialogue_parts,
                sound_parts,
            )
        return (dialogue_parts, sound_parts)

    @staticmethod
    def _finalize_sequence(
        seq_type: str,
        words: List[Dict[str, Any]],
        start: float,
        dialogue_parts: List[Dict[str, Any]],
        sound_parts: List[Dict[str, Any]],
    ) -> None:
        non_spacing = [w for w in words if w.get(WordKeys.TYPE) != WordTypeValues.SPACING]
        if not non_spacing:
            return
        text = ''.join((w.get(WordKeys.TEXT, '') for w in words))
        end = words[-1].get(WordKeys.END, start)
        new_segment = {
            'id': 0,
            'text': text,
            WordKeys.START: start,
            WordKeys.END: end,
            WordKeys.WORDS: words,
        }
        if seq_type == 'sound':
            new_segment['sound_type'] = 'sound'
            sound_parts.append(new_segment)
        else:
            dialogue_parts.append(new_segment)

    @staticmethod
    def _clean_segment_text(segment: Dict[str, Any]) -> Dict[str, Any]:
        cleaned = segment.copy()
        text = cleaned.get('text', '')
        text = re.sub('\\s+', ' ', text)
        cleaned['text'] = text.strip()
        words = cleaned.get(WordKeys.WORDS, [])
        if words:
            non_spacing = [w for w in words if w.get(WordKeys.TYPE) != WordTypeValues.SPACING]
            if non_spacing:
                cleaned[WordKeys.START] = min((w.get(WordKeys.START, 0) for w in non_spacing))
                cleaned[WordKeys.END] = max((w.get(WordKeys.END, 0) for w in non_spacing))
        return cleaned

    @staticmethod
    def _renumber_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for i, seg in enumerate(segments):
            seg['id'] = i
        return segments

    @staticmethod
    def _generate_txt_file(json_path: Path, txt_path: Path) -> None:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        segments = data.get('segments', [])
        text_lines = []
        for seg in segments:
            text = seg.get('text', '').strip()
            text = re.sub('\\([^)]*\\)', '', text)
            text = re.sub('\\s+', ' ', text).strip()
            if text:
                text_lines.append(text)
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(' '.join(text_lines))

    @staticmethod
    def _generate_srt_file(segments: List[Dict[str, Any]], srt_path: Path) -> None:
        with open(srt_path, 'w', encoding='utf-8') as f:
            for idx, seg in enumerate(segments, 1):
                start = seg.get('start', 0)
                end = seg.get('end', 0)
                text = seg.get('text', '').strip()
                start_time = SoundSeparationStep._format_srt_time(start)
                end_time = SoundSeparationStep._format_srt_time(end)
                f.write(f'{idx}\n')
                f.write(f'{start_time} --> {end_time}\n')
                f.write(f'{text}\n\n')

    @staticmethod
    def _format_srt_time(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int(seconds % 3600 // 60)
        secs = int(seconds % 60)
        millis = int(seconds % 1 * 1000)
        return f'{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}'

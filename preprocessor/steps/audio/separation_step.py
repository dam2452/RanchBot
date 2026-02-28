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
from preprocessor.core.temp_files import StepTempFile
from preprocessor.services.io.files import FileOperations
from preprocessor.services.transcription.sound_classification import (
    classify_segment,
    is_sound_event,
)


class SoundSeparationStep(
    PipelineStep[TranscriptionData, TranscriptionData, SoundSeparationConfig],
):
    @property
    def supports_batch_processing(self) -> bool:
        return True

    def execute_batch(
        self, input_data: List[TranscriptionData], context: ExecutionContext,
    ) -> List[TranscriptionData]:
        return self._execute_with_threadpool(
            input_data, context, self.config.max_parallel_episodes, self.execute,
        )

    def _process(
        self, input_data: TranscriptionData, context: ExecutionContext,
    ) -> TranscriptionData:
        output_paths = self.__resolve_output_paths(input_data)

        transcription_data = self.__load_transcription_payload(input_data)
        dialogue_segments, sound_segments = self.__separate_dialogue_from_sounds(
            transcription_data['segments'],
        )

        self.__save_separated_data(
            output_paths,
            transcription_data['episode_info'],
            dialogue_segments,
            sound_segments,
        )
        self.__generate_additional_formats(
            output_paths,
            dialogue_segments,
            sound_segments,
        )

        return self.__construct_result_artifact(output_paths, input_data)

    def _get_cache_path(
        self, input_data: TranscriptionData, context: ExecutionContext,
    ) -> Path:
        output_paths = self.__resolve_output_paths(input_data)
        return output_paths['clean_json']

    def _load_from_cache(
        self,
        cache_path: Path,
        input_data: TranscriptionData,
        context: ExecutionContext,
    ) -> TranscriptionData:
        output_paths = self.__resolve_output_paths(input_data)
        return self.__construct_result_artifact(output_paths, input_data)

    def __separate_dialogue_from_sounds(
        self,
        segments: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        dialogue_segments = []
        sound_segments = []

        for segment in segments:
            classification = classify_segment(segment)
            if classification == 'dialogue':
                cleaned = self.__clean_segment_text(segment)
                dialogue_segments.append(cleaned)
            elif classification == 'sound_event':
                cleaned = self.__clean_segment_text(segment)
                cleaned['sound_type'] = 'sound'
                sound_segments.append(cleaned)
            elif classification == 'mixed':
                dialogue_parts, sound_parts = self.__split_mixed_segment(segment)
                dialogue_segments.extend(dialogue_parts)
                sound_segments.extend(sound_parts)

        dialogue_segments = self.__renumber_segments(dialogue_segments)
        sound_segments = self.__renumber_segments(sound_segments)

        return dialogue_segments, sound_segments

    def __split_mixed_segment(
        self,
        segment: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        words = segment.get(WordKeys.WORDS, [])
        dialogue_parts = []
        sound_parts = []
        current_type = None
        current_words = []
        current_start = segment.get(WordKeys.START, 0.0)

        for word in words:
            word_type = 'sound' if is_sound_event(word) else 'dialogue'
            if word.get(WordKeys.TYPE) == WordTypeValues.SPACING:
                if current_words:
                    current_words.append(word)
                continue

            if word_type != current_type:
                if current_words and current_type:
                    self.__finalize_sequence(
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
            self.__finalize_sequence(
                current_type,
                current_words,
                current_start,
                dialogue_parts,
                sound_parts,
            )

        return dialogue_parts, sound_parts

    @staticmethod
    def __finalize_sequence(
            seq_type: str,
        words: List[Dict[str, Any]],
        start: float,
        dialogue_parts: List[Dict[str, Any]],
        sound_parts: List[Dict[str, Any]],
    ) -> None:
        non_spacing = [
            w for w in words if w.get(WordKeys.TYPE) != WordTypeValues.SPACING
        ]
        if not non_spacing:
            return

        text = ''.join((w.get(WordKeys.TEXT, '') for w in words))
        # Use the end time of the last word, or start if not available
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

    def __generate_additional_formats(
        self,
        output_paths: Dict[str, Path],
        dialogue_segments: List[Dict[str, Any]],
        sound_segments: List[Dict[str, Any]],
    ) -> None:
        self.__generate_txt_file(
            output_paths['clean_json'], output_paths['clean_txt'],
        )
        self.__generate_txt_file(
            output_paths['sound_json'], output_paths['sound_txt'],
        )
        self.__generate_srt_file(dialogue_segments, output_paths['clean_srt'])
        self.__generate_srt_file(sound_segments, output_paths['sound_srt'])

    @staticmethod
    def __resolve_output_paths(input_data: TranscriptionData) -> Dict[str, Path]:
        base_name = input_data.path.stem.replace(FILE_SUFFIXES['segmented'], '')
        episode_dir = input_data.path.parent.parent
        clean_dir = episode_dir / 'clean'
        sound_dir = episode_dir / 'sound_events'

        clean_dir.mkdir(parents=True, exist_ok=True)
        sound_dir.mkdir(parents=True, exist_ok=True)

        return {
            'clean_json': clean_dir
            / f"{base_name}{FILE_SUFFIXES['clean']}{FILE_EXTENSIONS['json']}",
            'sound_json': sound_dir
            / f"{base_name}{FILE_SUFFIXES['sound_events']}{FILE_EXTENSIONS['json']}",
            'clean_segmented': clean_dir
            / f"{base_name}{FILE_SUFFIXES['segmented']}_clean{FILE_EXTENSIONS['json']}",
            'sound_segmented': sound_dir
            / f"{base_name}{FILE_SUFFIXES['segmented']}_sound_events{FILE_EXTENSIONS['json']}",
            'clean_txt': clean_dir
            / f"{base_name}{FILE_SUFFIXES['clean']}{FILE_EXTENSIONS['txt']}",
            'sound_txt': sound_dir
            / f"{base_name}{FILE_SUFFIXES['sound_events']}{FILE_EXTENSIONS['txt']}",
            'clean_srt': clean_dir
            / f"{base_name}{FILE_SUFFIXES['clean']}{FILE_EXTENSIONS['srt']}",
            'sound_srt': sound_dir
            / f"{base_name}{FILE_SUFFIXES['sound_events']}{FILE_EXTENSIONS['srt']}",
        }

    @staticmethod
    def __load_transcription_payload(
        input_data: TranscriptionData,
    ) -> Dict[str, Any]:
        with open(input_data.path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {
            'episode_info': data.get('episode_info', {}),
            'segments': data.get('segments', []),
        }

    @staticmethod
    def __save_separated_data(
        output_paths: Dict[str, Path],
        episode_info_dict: Dict[str, Any],
        dialogue_segments: List[Dict[str, Any]],
        sound_segments: List[Dict[str, Any]],
    ) -> None:
        clean_data = {
            'episode_info': episode_info_dict,
            'segments': dialogue_segments,
        }
        sound_data = {'episode_info': episode_info_dict, 'segments': sound_segments}

        FileOperations.atomic_write_json(output_paths['clean_json'], clean_data)
        FileOperations.atomic_write_json(output_paths['sound_json'], sound_data)
        FileOperations.atomic_write_json(
            output_paths['clean_segmented'], clean_data,
        )
        FileOperations.atomic_write_json(
            output_paths['sound_segmented'], sound_data,
        )

    @staticmethod
    def __construct_result_artifact(
        output_paths: Dict[str, Path],
        input_data: TranscriptionData,
    ) -> TranscriptionData:
        return TranscriptionData(
            path=output_paths['clean_json'],
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            language=input_data.language,
            model=input_data.model,
            format='json',
        )

    @staticmethod
    def __clean_segment_text(segment: Dict[str, Any]) -> Dict[str, Any]:
        cleaned = segment.copy()
        text = cleaned.get('text', '')
        text = re.sub(r'\s+', ' ', text)
        cleaned['text'] = text.strip()
        words = cleaned.get(WordKeys.WORDS, [])

        if words:
            non_spacing = [
                w for w in words if w.get(WordKeys.TYPE) != WordTypeValues.SPACING
            ]
            if non_spacing:
                cleaned[WordKeys.START] = min(
                    (w.get(WordKeys.START, 0) for w in non_spacing),
                )
                cleaned[WordKeys.END] = max(
                    (w.get(WordKeys.END, 0) for w in non_spacing),
                )

        return cleaned

    @staticmethod
    def __format_srt_time(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int(seconds % 3600 // 60)
        secs = int(seconds % 60)
        millis = int(seconds % 1 * 1000)
        return f'{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}'

    @staticmethod
    def __generate_srt_file(
        segments: List[Dict[str, Any]], srt_path: Path,
    ) -> None:
        with StepTempFile(srt_path) as temp_path:
            with open(temp_path, 'w', encoding='utf-8') as f:
                for idx, seg in enumerate(segments, 1):
                    start = seg.get('start', 0)
                    end = seg.get('end', 0)
                    text = seg.get('text', '').strip()

                    start_time = SoundSeparationStep.__format_srt_time(start)
                    end_time = SoundSeparationStep.__format_srt_time(end)

                    f.write(f'{idx}\n')
                    f.write(f'{start_time} --> {end_time}\n')
                    f.write(f'{text}\n\n')

    @staticmethod
    def __generate_txt_file(json_path: Path, txt_path: Path) -> None:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        segments = data.get('segments', [])
        text_lines = []

        for seg in segments:
            text = seg.get('text', '').strip()
            text = re.sub(r'\([^)]*\)', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
            if text:
                text_lines.append(text)

        with StepTempFile(txt_path) as temp_path:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(' '.join(text_lines))

    @staticmethod
    def __renumber_segments(
        segments: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        for i, seg in enumerate(segments):
            seg['id'] = i
        return segments

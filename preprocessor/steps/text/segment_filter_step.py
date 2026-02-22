from abc import abstractmethod
from pathlib import Path
import re
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    TypeVar,
)

from preprocessor.config.step_configs import SegmentFilterConfig
from preprocessor.config.types import (
    WordKeys,
    WordTypeValues,
)
from preprocessor.core.artifacts import TranscriptionData
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.core.output_descriptors import JsonFileOutput
from preprocessor.services.io.files import FileOperations
from preprocessor.services.transcription.sound_classification import (
    classify_segment,
    is_sound_event,
)

_ConfigT = TypeVar('_ConfigT', bound=SegmentFilterConfig)

_SOUND_EVENT_PATTERN = re.compile(r'^\s*\(.*\)\s*$')


class SegmentFilterStep(
    PipelineStep[TranscriptionData, TranscriptionData, _ConfigT],
    Generic[_ConfigT],
):
    @property
    @abstractmethod
    def _output_format(self) -> str:
        pass

    @abstractmethod
    def _process_segment(self, segment: Dict[str, Any]) -> List[Dict[str, Any]]:
        pass

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
        output_path = self._get_cache_path(input_data, context)
        data = FileOperations.load_json(input_data.path)
        filtered = self.__apply_filter(data)
        FileOperations.atomic_write_json(output_path, filtered)
        return self.__build_artifact(input_data, output_path)

    def get_output_descriptors(self) -> List[JsonFileOutput]:
        return [
            JsonFileOutput(
                pattern="{season}/{episode}.json",
                subdir="",
                min_size_bytes=10,
            ),
        ]

    def _get_cache_path(
            self, input_data: TranscriptionData, context: ExecutionContext,
    ) -> Path:
        return self._get_standard_cache_path(input_data, context)

    def _load_from_cache(
            self,
            cache_path: Path,
            input_data: TranscriptionData,
            context: ExecutionContext,
    ) -> TranscriptionData:
        return self.__build_artifact(input_data, cache_path)

    @staticmethod
    def _classify(segment: Dict[str, Any]) -> str:
        words = segment.get(WordKeys.WORDS, [])
        if not words:
            text = segment.get('text', '').strip()
            return 'sound_event' if _SOUND_EVENT_PATTERN.match(text) else 'dialogue'
        return classify_segment(segment)

    @staticmethod
    def _split_mixed(
            segment: Dict[str, Any],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        words = segment.get(WordKeys.WORDS, [])

        dialogue_words = [
            w for w in words
            if not is_sound_event(w) and w.get(WordKeys.TYPE) not in (WordTypeValues.SPACING, '')
        ]
        sound_words = [w for w in words if is_sound_event(w)]

        dialogue_part = SegmentFilterStep.__make_sub_segment(segment, dialogue_words) if dialogue_words else None
        sound_part = SegmentFilterStep.__make_sub_segment(segment, sound_words) if sound_words else None

        return dialogue_part, sound_part

    @staticmethod
    def __make_sub_segment(
            segment: Dict[str, Any],
            words: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        text = ' '.join(w.get(WordKeys.TEXT, w.get(WordKeys.WORD, '')) for w in words).strip()
        return {
            **segment,
            'start': words[0].get(WordKeys.START, segment.get('start')),
            'end': words[-1].get(WordKeys.END, segment.get('end')),
            'text': text,
            WordKeys.WORDS: words,
        }

    def __apply_filter(self, data: Dict[str, Any]) -> Dict[str, Any]:
        segments: List[Dict[str, Any]] = data.get('segments', [])
        result: List[Dict[str, Any]] = []
        for seg in segments:
            result.extend(self._process_segment(seg))
        return {**data, 'segments': result}

    def __build_artifact(self, input_data: TranscriptionData, path: Path) -> TranscriptionData:
        return TranscriptionData(
            episode_id=input_data.episode_id,
            episode_info=input_data.episode_info,
            path=path,
            language=input_data.language,
            model=input_data.model,
            format=self._output_format,
        )

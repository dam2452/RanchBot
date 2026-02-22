from typing import (
    Any,
    Dict,
    List,
)

from preprocessor.config.step_configs import TextCleaningConfig
from preprocessor.steps.text.segment_filter_step import SegmentFilterStep


class TextCleaningStep(SegmentFilterStep[TextCleaningConfig]):
    @property
    def _output_format(self) -> str:
        return 'clean'

    def _process_segment(self, segment: Dict[str, Any]) -> List[Dict[str, Any]]:
        kind = self._classify(segment)
        if kind == 'dialogue':
            return [segment]
        if kind == 'sound_event':
            return []
        dialogue_part, _ = self._split_mixed(segment)
        return [dialogue_part] if dialogue_part else []

from typing import (
    Any,
    Dict,
    List,
)

from preprocessor.config.step_configs import SoundEventsConfig
from preprocessor.steps.text.segment_filter_step import SegmentFilterStep


class SoundEventsStep(SegmentFilterStep[SoundEventsConfig]):
    @property
    def _output_format(self) -> str:
        return 'sound_events'

    def _process_segment(self, segment: Dict[str, Any]) -> List[Dict[str, Any]]:
        kind = self._classify(segment)
        if kind == 'sound_event':
            return [segment]
        if kind == 'dialogue':
            return []
        _, sound_part = self._split_mixed(segment)
        return [sound_part] if sound_part else []

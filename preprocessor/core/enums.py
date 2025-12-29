from enum import Enum


class KeyframeStrategy(str, Enum):
    KEYFRAMES = "keyframes"
    SCENE_CHANGES = "scene_changes"
    COLOR_DIFF = "color_diff"


class FrameType(str, Enum):
    KEYFRAME = "keyframe"
    SCENE_SINGLE = "scene_single"
    SCENE_START = "scene_start"
    SCENE_END = "scene_end"
    COLOR_CHANGE = "color_change"

    @staticmethod
    def scene_mid(index: int) -> str:
        return f"scene_mid_{index}"


class ScraperMethod(str, Enum):
    CLIPBOARD = "clipboard"
    CRAWL4AI = "crawl4ai"


class ParserMode(str, Enum):
    NORMAL = "normal"
    PREMIUM = "premium"


class TranscriptionFormat(str, Enum):
    ELEVENLABS_SEGMENTED = "11labs_segmented"
    ELEVENLABS = "11labs"


class Device(str, Enum):
    CUDA = "cuda"
    CPU = "cpu"

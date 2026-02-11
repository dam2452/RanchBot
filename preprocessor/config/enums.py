from enum import Enum


class KeyframeStrategy(str, Enum):
    SCENE_CHANGES = 'scene_changes'

class FrameType(str, Enum):
    SCENE_END = 'scene_end'
    SCENE_SINGLE = 'scene_single'
    SCENE_START = 'scene_start'

    @staticmethod
    def scene_mid(index: int) -> str:
        return f'scene_mid_{index}'

class ScraperMethod(str, Enum):
    CLIPBOARD = 'clipboard'
    CRAWL4AI = 'crawl4ai'

class ParserMode(str, Enum):
    NORMAL = 'normal'
    PREMIUM = 'premium'

class TranscriptionFormat(str, Enum):
    ELEVENLABS = '11labs'
    ELEVENLABS_SEGMENTED = '11labs_segmented'

class Device(str, Enum):
    CPU = 'cpu'
    CUDA = 'cuda'

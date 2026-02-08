# pylint: disable=duplicate-code

class SegmentKeys:
    START_TIME = "start_time"
    END_TIME = "end_time"
    TEXT = "text"
    VIDEO_PATH = "video_path"
    SEGMENT_ID = "segment_id"
    ID = "id"
    START = "start"
    END = "end"


class EpisodeMetadataKeys:
    EPISODE_METADATA = "episode_metadata"
    EPISODE_INFO = "episode_info"
    SEASON = "season"
    EPISODE_NUMBER = "episode_number"
    SERIES_NAME = "series_name"
    TITLE = "title"
    PREMIERE_DATE = "premiere_date"
    VIEWERSHIP = "viewership"


class ElasticsearchKeys:
    SOURCE = "_source"
    SCORE = "_score"
    HITS = "hits"
    TOTAL = "total"
    AGGREGATIONS = "aggregations"
    BUCKETS = "buckets"
    KEY = "key"


class ElasticsearchAggregationKeys:
    UNIQUE_EPISODES = "unique_episodes"
    SEASONS = "seasons"
    VALUE = "value"


class TranscriptionContextKeys:
    TARGET = "target"
    CONTEXT = "context"
    OVERALL_START_TIME = "overall_start_time"
    OVERALL_END_TIME = "overall_end_time"


class ElasticsearchQueryKeys:
    QUERY = "query"
    TERM = "term"
    MATCH = "match"
    BOOL = "bool"
    MUST = "must"
    FILTER = "filter"
    RANGE = "range"
    SIZE = "size"
    SORT = "sort"
    ORDER = "order"
    ASC = "asc"
    DESC = "desc"
    FUZZINESS = "fuzziness"
    AUTO = "AUTO"
    TERMS = "terms"
    FIELD = "field"
    AGGS = "aggs"
    CARDINALITY = "cardinality"
    TOP_HITS = "top_hits"
    INCLUDES = "includes"
    LT = "lt"
    GT = "gt"
    SOURCE = "_source"
    KEY = "_key"


class EpisodesDataKeys:
    SEASONS = "seasons"
    SEASON_NUMBER = "season_number"
    EPISODES = "episodes"


class FfprobeKeys:
    STREAMS = "streams"
    FORMAT = "format"


class FfprobeStreamKeys:
    R_FRAME_RATE = "r_frame_rate"
    BIT_RATE = "bit_rate"
    CODEC_NAME = "codec_name"
    WIDTH = "width"
    HEIGHT = "height"
    DURATION = "duration"


class FfprobeFormatKeys:
    DURATION = "duration"
    SIZE = "size"


class DetectionKeys:
    DETECTIONS = "detections"
    CHARACTERS = "characters"
    FRAME_NUMBER = "frame_number"
    FRAME = "frame"
    FRAME_NAME = "frame_name"
    FRAME_FILE = "frame_file"


class CharacterDetectionKeys:
    NAME = "name"
    CONFIDENCE = "confidence"
    EMOTION = "emotion"
    BBOX = "bbox"


class EmotionKeys:
    LABEL = "label"
    CONFIDENCE = "confidence"


class ObjectDetectionKeys:
    CLASS_NAME = "class_name"
    CLASS_ID = "class_id"
    CONFIDENCE = "confidence"
    BBOX = "bbox"


class SceneKeys:
    SCENES = "scenes"
    START = "start"
    END = "end"
    SCENE_NUMBER = "scene_number"
    SCENE_START_FRAME = "scene_start_frame"
    SCENE_END_FRAME = "scene_end_frame"
    SCENE_START_TIME = "scene_start_time"
    SCENE_END_TIME = "scene_end_time"


class SceneTimeKeys:
    SECONDS = "seconds"
    FRAME = "frame"


class ElasticDocKeys:
    SCENE_INFO = "scene_info"
    CHARACTER_APPEARANCES = "character_appearances"
    DETECTED_OBJECTS = "detected_objects"
    PERCEPTUAL_HASH = "perceptual_hash"
    PERCEPTUAL_HASH_INT = "perceptual_hash_int"


class EmbeddingKeys:
    EPISODE_ID = "episode_id"
    TITLE = "title"
    TITLE_EMBEDDING = "title_embedding"
    EPISODE_METADATA = "episode_metadata"
    FRAME_NUMBER = "frame_number"
    PERCEPTUAL_HASH = "perceptual_hash"
    FRAME_PATH = "frame_path"
    TIMESTAMP = "timestamp"
    EMBEDDING = "embedding"
    SCENE_NUMBER = "scene_number"


class ValidationMetadataKeys:
    WIDTH = "width"
    HEIGHT = "height"
    FORMAT = "format"
    SIZE_MB = "size_mb"
    SIZE_BYTES = "size_bytes"
    LINE_COUNT = "line_count"
    CODEC = "codec"
    DURATION = "duration"


class WordKeys:
    TYPE = "type"
    START = "start"
    END = "end"
    WORD = "word"


class WordTypeValues:
    SPACING = "spacing"
    AUDIO_EVENT = "audio_event"


class GoogleSearchKeys:
    ENGINE = "engine"
    Q = "q"
    HL = "hl"
    GL = "gl"
    API_KEY = "api_key"
    IMAGES_RESULTS = "images_results"


class ImageResultKeys:
    ORIGINAL = "original"
    THUMBNAIL = "thumbnail"
    IMAGE = "image"

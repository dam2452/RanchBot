class SegmentKeys:
    END = 'end'
    END_TIME = 'end_time'
    ID = 'id'
    SEGMENT_ID = 'segment_id'
    START = 'start'
    START_TIME = 'start_time'
    TEXT = 'text'
    VIDEO_PATH = 'video_path'

class EpisodeMetadataKeys:
    EPISODE_INFO = 'episode_info'
    EPISODE_METADATA = 'episode_metadata'
    EPISODE_NUMBER = 'episode_number'
    PREMIERE_DATE = 'premiere_date'
    SEASON = 'season'
    SERIES_NAME = 'series_name'
    TITLE = 'title'
    VIEWERSHIP = 'viewership'

class ElasticsearchKeys:
    AGGREGATIONS = 'aggregations'
    BUCKETS = 'buckets'
    HITS = 'hits'
    KEY = 'key'
    SCORE = '_score'
    SOURCE = '_source'
    TOTAL = 'total'

class ElasticsearchAggregationKeys:
    SEASONS = 'seasons'
    UNIQUE_EPISODES = 'unique_episodes'
    VALUE = 'value'

class TranscriptionContextKeys:
    CONTEXT = 'context'
    OVERALL_END_TIME = 'overall_end_time'
    OVERALL_START_TIME = 'overall_start_time'
    TARGET = 'target'

class ElasticsearchQueryKeys:
    AGGS = 'aggs'
    ASC = 'asc'
    AUTO = 'AUTO'
    BOOL = 'bool'
    CARDINALITY = 'cardinality'
    DESC = 'desc'
    FIELD = 'field'
    FILTER = 'filter'
    FUZZINESS = 'fuzziness'
    GT = 'gt'
    INCLUDES = 'includes'
    KEY = '_key'
    LT = 'lt'
    MATCH = 'match'
    MUST = 'must'
    ORDER = 'order'
    QUERY = 'query'
    RANGE = 'range'
    SIZE = 'size'
    SORT = 'sort'
    SOURCE = '_source'
    TERM = 'term'
    TERMS = 'terms'
    TOP_HITS = 'top_hits'

class EpisodesDataKeys:
    EPISODES = 'episodes'
    SEASONS = 'seasons'
    SEASON_NUMBER = 'season_number'

class FfprobeKeys:
    FORMAT = 'format'
    STREAMS = 'streams'

class FfprobeStreamKeys:
    BIT_RATE = 'bit_rate'
    CODEC_NAME = 'codec_name'
    DURATION = 'duration'
    HEIGHT = 'height'
    R_FRAME_RATE = 'r_frame_rate'
    WIDTH = 'width'

class FfprobeFormatKeys:
    DURATION = 'duration'
    SIZE = 'size'

class DetectionKeys:
    CHARACTERS = 'characters'
    DETECTIONS = 'detections'
    FRAME = 'frame'
    FRAME_FILE = 'frame_file'
    FRAME_NAME = 'frame_name'
    FRAME_NUMBER = 'frame_number'

class CharacterDetectionKeys:
    BBOX = 'bbox'
    CONFIDENCE = 'confidence'
    EMOTION = 'emotion'
    NAME = 'name'

class EmotionKeys:
    CONFIDENCE = 'confidence'
    LABEL = 'label'

class ObjectDetectionKeys:
    BBOX = 'bbox'
    CLASS_ID = 'class_id'
    CLASS_NAME = 'class_name'
    CONFIDENCE = 'confidence'

class SceneKeys:
    END = 'end'
    SCENES = 'scenes'
    SCENE_END_FRAME = 'scene_end_frame'
    SCENE_END_TIME = 'scene_end_time'
    SCENE_NUMBER = 'scene_number'
    SCENE_START_FRAME = 'scene_start_frame'
    SCENE_START_TIME = 'scene_start_time'
    START = 'start'

class SceneTimeKeys:
    FRAME = 'frame'
    SECONDS = 'seconds'

class ElasticDocKeys:
    CHARACTER_APPEARANCES = 'character_appearances'
    DETECTED_OBJECTS = 'detected_objects'
    PERCEPTUAL_HASH = 'perceptual_hash'
    PERCEPTUAL_HASH_INT = 'perceptual_hash_int'
    SCENE_INFO = 'scene_info'

class EmbeddingKeys:
    EMBEDDING = 'embedding'
    EPISODE_ID = 'episode_id'
    EPISODE_METADATA = 'episode_metadata'
    FRAME_NUMBER = 'frame_number'
    FRAME_PATH = 'frame_path'
    PERCEPTUAL_HASH = 'perceptual_hash'
    SCENE_NUMBER = 'scene_number'
    TIMESTAMP = 'timestamp'
    TITLE = 'title'
    TITLE_EMBEDDING = 'title_embedding'

class ValidationMetadataKeys:
    CODEC = 'codec'
    DURATION = 'duration'
    FORMAT = 'format'
    HEIGHT = 'height'
    LINE_COUNT = 'line_count'
    SIZE_BYTES = 'size_bytes'
    SIZE_MB = 'size_mb'
    WIDTH = 'width'

class WordKeys:
    END = 'end'
    START = 'start'
    TEXT = 'text'
    TYPE = 'type'
    WORD = 'word'
    WORDS = 'words'

class WordTypeValues:
    AUDIO_EVENT = 'audio_event'
    SPACING = 'spacing'

class GoogleSearchKeys:
    API_KEY = 'api_key'
    ENGINE = 'engine'
    GL = 'gl'
    HL = 'hl'
    IMAGES_RESULTS = 'images_results'
    Q = 'q'

class ImageResultKeys:
    IMAGE = 'image'
    ORIGINAL = 'original'
    THUMBNAIL = 'thumbnail'

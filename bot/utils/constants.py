# pylint: disable=duplicate-code
from typing import Final


class SegmentKeys:
    START_TIME: Final[str] = "start_time"
    END_TIME: Final[str] = "end_time"
    TEXT: Final[str] = "text"
    VIDEO_PATH: Final[str] = "video_path"
    SEGMENT_ID: Final[str] = "segment_id"
    ID: Final[str] = "id"
    START: Final[str] = "start"
    END: Final[str] = "end"


class EpisodeMetadataKeys:
    EPISODE_METADATA: Final[str] = "episode_metadata"
    EPISODE_INFO: Final[str] = "episode_info"
    SEASON: Final[str] = "season"
    EPISODE_NUMBER: Final[str] = "episode_number"
    SERIES_NAME: Final[str] = "series_name"
    TITLE: Final[str] = "title"
    PREMIERE_DATE: Final[str] = "premiere_date"
    VIEWERSHIP: Final[str] = "viewership"
    SEASON_FIELD: Final[str] = f"{EPISODE_METADATA}.{SEASON}"
    EPISODE_NUMBER_FIELD: Final[str] = f"{EPISODE_METADATA}.{EPISODE_NUMBER}"
    SERIES_NAME_FIELD: Final[str] = f"{EPISODE_METADATA}.{SERIES_NAME}"
    TITLE_FIELD: Final[str] = f"{EPISODE_METADATA}.{TITLE}"
    PREMIERE_DATE_FIELD: Final[str] = f"{EPISODE_METADATA}.{PREMIERE_DATE}"
    VIEWERSHIP_FIELD: Final[str] = f"{EPISODE_METADATA}.{VIEWERSHIP}"


class ElasticsearchKeys:
    SOURCE: Final[str] = "_source"
    SCORE: Final[str] = "_score"
    HITS: Final[str] = "hits"
    TOTAL: Final[str] = "total"
    AGGREGATIONS: Final[str] = "aggregations"
    BUCKETS: Final[str] = "buckets"
    KEY: Final[str] = "key"
    DOC_COUNT: Final[str] = "doc_count"


class ElasticsearchAggregationKeys:
    UNIQUE_EPISODES: Final[str] = "unique_episodes"
    SEASONS: Final[str] = "seasons"
    VALUE: Final[str] = "value"
    ACTORS: Final[str] = "actors"
    EMOTION_LABELS: Final[str] = "emotion_labels"
    UNIQUE_EPISODE_KEYS: Final[str] = "unique_episode_keys"
    NAMES: Final[str] = "names"
    OBJECTS: Final[str] = "objects"
    CLASSES: Final[str] = "classes"
    BACK_TO_ROOT: Final[str] = "back_to_root"
    SOUND_TYPES: Final[str] = "sound_types"
    UNIQUE_SCENES: Final[str] = "unique_scenes"
    SCENE_START: Final[str] = "scene_start"
    SCENE_END: Final[str] = "scene_end"


class ActorKeys:
    ACTORS: Final[str] = "character_appearances"
    NAME: Final[str] = "name"
    CONFIDENCE: Final[str] = "confidence"
    EMOTION: Final[str] = "emotion"


class EmotionKeys:
    LABEL: Final[str] = "label"
    CONFIDENCE: Final[str] = "confidence"


class TranscriptionContextKeys:
    TARGET: Final[str] = "target"
    CONTEXT: Final[str] = "context"
    OVERALL_START_TIME: Final[str] = "overall_start_time"
    OVERALL_END_TIME: Final[str] = "overall_end_time"


class ElasticsearchQueryKeys:
    QUERY: Final[str] = "query"
    TERM: Final[str] = "term"
    MATCH: Final[str] = "match"
    BOOL: Final[str] = "bool"
    MUST: Final[str] = "must"
    FILTER: Final[str] = "filter"
    RANGE: Final[str] = "range"
    SIZE: Final[str] = "size"
    SORT: Final[str] = "sort"
    ORDER: Final[str] = "order"
    ASC: Final[str] = "asc"
    DESC: Final[str] = "desc"
    FUZZINESS: Final[str] = "fuzziness"
    AUTO: Final[str] = "AUTO"
    TERMS: Final[str] = "terms"
    FIELD: Final[str] = "field"
    AGGS: Final[str] = "aggs"
    CARDINALITY: Final[str] = "cardinality"
    TOP_HITS: Final[str] = "top_hits"
    INCLUDES: Final[str] = "includes"
    LT: Final[str] = "lt"
    GT: Final[str] = "gt"
    SOURCE: Final[str] = "_source"
    KEY: Final[str] = "_key"
    EXISTS: Final[str] = "exists"
    MUST_NOT: Final[str] = "must_not"
    NESTED: Final[str] = "nested"
    REVERSE_NESTED: Final[str] = "reverse_nested"
    VALUE: Final[str] = "value"
    CASE_INSENSITIVE: Final[str] = "case_insensitive"
    MINIMUM_SHOULD_MATCH: Final[str] = "minimum_should_match"
    MODE: Final[str] = "mode"
    PATH: Final[str] = "path"
    MAX: Final[str] = "max"
    SHOULD: Final[str] = "should"
    GTE: Final[str] = "gte"
    LTE: Final[str] = "lte"
    SEARCH_AFTER: Final[str] = "search_after"
    COMPOSITE: Final[str] = "composite"
    SOURCES: Final[str] = "sources"
    AFTER: Final[str] = "after"
    AFTER_KEY: Final[str] = "after_key"


class DatabaseKeys:
    ID: Final[str] = "id"
    SERIES_ID: Final[str] = "series_id"
    SERIES_NAME: Final[str] = "series_name"
    USER_ID: Final[str] = "user_id"
    USERNAME: Final[str] = "username"
    FULL_NAME: Final[str] = "full_name"
    SUBSCRIPTION_END: Final[str] = "subscription_end"
    NOTE: Final[str] = "note"
    IS_ADMIN: Final[str] = "is_admin"
    IS_MODERATOR: Final[str] = "is_moderator"
    CLIP_NAME: Final[str] = "clip_name"
    VIDEO_DATA: Final[str] = "video_data"
    START_TIME: Final[str] = "start_time"
    END_TIME: Final[str] = "end_time"
    DURATION: Final[str] = "duration"
    SEASON: Final[str] = "season"
    EPISODE_NUMBER: Final[str] = "episode_number"
    IS_COMPILATION: Final[str] = "is_compilation"
    QUOTE: Final[str] = "quote"
    SEGMENTS: Final[str] = "segments"
    SEGMENT: Final[str] = "segment"
    COMPILED_CLIP: Final[str] = "compiled_clip"
    CLIP_TYPE: Final[str] = "clip_type"
    ADJUSTED_START_TIME: Final[str] = "adjusted_start_time"
    ADJUSTED_END_TIME: Final[str] = "adjusted_end_time"
    IS_ADJUSTED: Final[str] = "is_adjusted"
    TIMESTAMP: Final[str] = "timestamp"
    DAYS: Final[str] = "days"
    MESSAGE: Final[str] = "message"
    REPORT: Final[str] = "report"
    TOKEN: Final[str] = "token"
    CREATED_AT: Final[str] = "created_at"
    EXPIRES_AT: Final[str] = "expires_at"
    REVOKED_AT: Final[str] = "revoked_at"
    IP_ADDRESS: Final[str] = "ip_address"
    USER_AGENT: Final[str] = "user_agent"
    HASHED_PASSWORD: Final[str] = "hashed_password"
    LAST_UPDATED: Final[str] = "last_updated"


class HttpHeaderKeys:
    USER_AGENT: Final[str] = "User-Agent"
    AUTHORIZATION: Final[str] = "Authorization"


class AuthKeys:
    REFRESH_TOKEN_COOKIE: Final[str] = "refresh_token"
    ACCESS_TOKEN: Final[str] = "access_token"
    TOKEN_TYPE: Final[str] = "token_type"
    BEARER: Final[str] = "bearer"


class JwtPayloadKeys:
    USER_ID: Final[str] = "user_id"
    USERNAME: Final[str] = "username"
    FULL_NAME: Final[str] = "full_name"
    EXP: Final[str] = "exp"
    IAT: Final[str] = "iat"
    ISS: Final[str] = "iss"
    AUD: Final[str] = "aud"


class ElasticsearchIndexSuffixes:
    TEXT_SEGMENTS: Final[str] = "_text_segments"
    VIDEO_FRAMES: Final[str] = "_video_frames"
    TEXT_EMBEDDINGS: Final[str] = "_text_embeddings"
    FULL_EPISODE_EMBEDDINGS: Final[str] = "_full_episode_embeddings"
    EPISODE_NAMES: Final[str] = "_episode_names"
    SOUND_EVENTS: Final[str] = "_sound_events"
    SOUND_EVENT_EMBEDDINGS: Final[str] = "_sound_event_embeddings"


class VideoFrameKeys:
    TIMESTAMP: Final[str] = "timestamp"
    FRAME_NUMBER: Final[str] = "frame_number"
    FRAME_TYPE: Final[str] = "frame_type"
    DETECTED_OBJECTS: Final[str] = "detected_objects"
    SCENE_INFO: Final[str] = "scene_info"
    EPISODE_ID: Final[str] = "episode_id"
    SCENE_NUMBER: Final[str] = "scene_number"


class DetectedObjectKeys:
    CLASS: Final[str] = "class"
    COUNT: Final[str] = "count"
    OBJECT_CLASS_FIELD: Final[str] = f"{VideoFrameKeys.DETECTED_OBJECTS}.{CLASS}"


class SceneInfoKeys:
    SCENE_NUMBER: Final[str] = "scene_number"
    SCENE_START_TIME: Final[str] = "scene_start_time"
    SCENE_END_TIME: Final[str] = "scene_end_time"


class SoundEventKeys:
    SOUND_TYPE: Final[str] = "sound_type"
    TEXT: Final[str] = "text"
    SOUND_TYPES: Final[str] = "sound_types"


class EmbeddingKeys:
    EPISODE_ID: Final[str] = "episode_id"
    EMBEDDING_ID: Final[str] = "embedding_id"
    SEGMENT_RANGE: Final[str] = "segment_range"
    FRAME_NUMBER: Final[str] = "frame_number"
    FULL_TRANSCRIPT: Final[str] = "full_transcript"
    TITLE_EMBEDDING: Final[str] = "title_embedding"
    TEXT_EMBEDDING: Final[str] = "text_embedding"
    VIDEO_EMBEDDING: Final[str] = "video_embedding"
    FULL_EPISODE_EMBEDDING: Final[str] = "full_episode_embedding"
    SOUND_EVENT_EMBEDDING: Final[str] = "sound_event_embedding"


class ResponseKeys:
    DATA: Final[str] = "data"
    MESSAGE: Final[str] = "message"
    CONTENT: Final[str] = "content"

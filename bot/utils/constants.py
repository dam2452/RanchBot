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


class ElasticsearchKeys:
    SOURCE: Final[str] = "_source"
    SCORE: Final[str] = "_score"
    HITS: Final[str] = "hits"
    TOTAL: Final[str] = "total"
    AGGREGATIONS: Final[str] = "aggregations"
    BUCKETS: Final[str] = "buckets"
    KEY: Final[str] = "key"


class ElasticsearchAggregationKeys:
    UNIQUE_EPISODES: Final[str] = "unique_episodes"
    SEASONS: Final[str] = "seasons"
    VALUE: Final[str] = "value"


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


class ResponseKeys:
    DATA: Final[str] = "data"
    MESSAGE: Final[str] = "message"
    CONTENT: Final[str] = "content"

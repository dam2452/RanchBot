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


class DatabaseKeys:
    ID = "id"
    SERIES_ID = "series_id"
    SERIES_NAME = "series_name"
    USER_ID = "user_id"
    USERNAME = "username"
    FULL_NAME = "full_name"
    SUBSCRIPTION_END = "subscription_end"
    NOTE = "note"
    IS_ADMIN = "is_admin"
    IS_MODERATOR = "is_moderator"
    CLIP_NAME = "clip_name"
    VIDEO_DATA = "video_data"
    START_TIME = "start_time"
    END_TIME = "end_time"
    DURATION = "duration"
    SEASON = "season"
    EPISODE_NUMBER = "episode_number"
    IS_COMPILATION = "is_compilation"
    QUOTE = "quote"
    SEGMENTS = "segments"
    SEGMENT = "segment"
    COMPILED_CLIP = "compiled_clip"
    CLIP_TYPE = "clip_type"
    ADJUSTED_START_TIME = "adjusted_start_time"
    ADJUSTED_END_TIME = "adjusted_end_time"
    IS_ADJUSTED = "is_adjusted"
    TIMESTAMP = "timestamp"
    DAYS = "days"
    MESSAGE = "message"
    REPORT = "report"
    TOKEN = "token"
    CREATED_AT = "created_at"
    EXPIRES_AT = "expires_at"
    REVOKED_AT = "revoked_at"
    IP_ADDRESS = "ip_address"
    USER_AGENT = "user_agent"
    HASHED_PASSWORD = "hashed_password"
    LAST_UPDATED = "last_updated"


class HttpHeaderKeys:
    USER_AGENT = "User-Agent"
    AUTHORIZATION = "Authorization"


class AuthKeys:
    REFRESH_TOKEN_COOKIE = "refresh_token"
    ACCESS_TOKEN = "access_token"
    TOKEN_TYPE = "token_type"
    BEARER = "bearer"


class JwtPayloadKeys:
    USER_ID = "user_id"
    USERNAME = "username"
    FULL_NAME = "full_name"
    EXP = "exp"
    IAT = "iat"
    ISS = "iss"
    AUD = "aud"


class ResponseKeys:
    DATA = "data"
    MESSAGE = "message"
    CONTENT = "content"

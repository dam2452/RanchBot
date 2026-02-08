# PRZEWODNIK IMPLEMENTACJI - REFAKTORYZACJA RAW STRINGÓW

## QUICK START - Co zrobić najpierw?

### Krok 1: Utworzyć nowe klasy w `bot/utils/constants.py`

```python
# bot/utils/constants.py

class ElasticsearchKeys:
    """Klucze używane w operacjach Elasticsearch."""

    # Mapping structure
    TYPE: str = "type"
    PROPERTIES: str = "properties"
    MAPPINGS: str = "mappings"

    # Response structure
    HITS: str = "hits"
    SOURCE: str = "_source"
    INDEX: str = "_index"
    ID: str = "_id"

    # Query DSL
    QUERY: str = "query"
    BOOL: str = "bool"
    MUST: str = "must"
    FILTER: str = "filter"
    TERM: str = "term"
    NESTED: str = "nested"
    PATH: str = "path"
    FIELD: str = "field"

    # Search operations
    MULTI_MATCH: str = "multi_match"
    RANGE: str = "range"
    FUZZINESS: str = "fuzziness"
    FIELDS: str = "fields"

    # KNN search
    KNN: str = "knn"
    QUERY_VECTOR: str = "query_vector"
    K: str = "k"
    NUM_CANDIDATES: str = "num_candidates"

    # Aggregations
    AGGS: str = "aggs"
    AGGREGATIONS: str = "aggregations"
    BUCKETS: str = "buckets"
    KEY: str = "key"
    DOC_COUNT: str = "doc_count"

    # Sorting
    SORT: str = "sort"
    ORDER: str = "order"
    ASC: str = "asc"
    DESC: str = "desc"

    # Count
    COUNT: str = "count"


class ElasticsearchIndexNames:
    """Nazwy indeksów Elasticsearch."""

    SEGMENTS: str = "ranczo_segments"
    TEXT_EMBEDDINGS: str = "ranczo_text_embeddings"
    VIDEO_FRAMES: str = "ranczo_video_frames"
    EPISODE_NAMES: str = "ranczo_episode_names"
    FULL_EPISODE_EMBEDDINGS: str = "ranczo_full_episode_embeddings"
    SOUND_EVENTS: str = "ranczo_sound_events"
    SOUND_EVENT_EMBEDDINGS: str = "ranczo_sound_event_embeddings"

    # Index type mappings
    TEXT_SEGMENTS: str = "text_segments"
    VIDEO_FRAMES_TYPE: str = "video_frames"


class ResponseDataKeys:
    """Klucze używane w odpowiedziach API."""

    # Response structure
    STATUS: str = "status"
    MESSAGE: str = "message"
    DATA: str = "data"
    CONTENT: str = "content"
    MARKDOWN: str = "markdown"

    # Data fields
    QUOTE: str = "quote"
    RESULTS: str = "results"
    SEGMENT: str = "segment"
    SEGMENTS: str = "segments"
    CLIPS: str = "clips"
    SEASON_INFO: str = "season_info"
    EPISODES: str = "episodes"
    SEASON: str = "season"

    # User management
    WHITELIST: str = "whitelist"
    MODERATORS: str = "moderators"
    ADMINS: str = "admins"

    # Subscription
    KEYS: str = "keys"
    DAYS: str = "days"
    KEY: str = "key"
    SUBSCRIPTION_END: str = "subscription_end"
    DAYS_REMAINING: str = "days_remaining"

    # Query
    QUERY: str = "query"
    ARGS: str = "args"
    REPLY_JSON: str = "reply_json"


class SegmentDataKeys:
    """Klucze danych segmentów transkrypcji (rozszerzenie SegmentKeys)."""

    # Basic segment data
    TEXT: str = "text"
    START: str = "start"
    END: str = "end"
    SEGMENTS: str = "segments"

    # Timing
    START_TIME: str = "start_time"
    END_TIME: str = "end_time"
    TIMESTAMP: str = "timestamp"

    # Metadata
    WORDS: str = "words"
    SPEAKER: str = "speaker"
    SPEAKER_ID: str = "speaker_id"
    SEGMENT_RANGE: str = "segment_range"

    # Additional fields
    SEEK: str = "seek"
    AUTHOR: str = "author"
    COMMENT: str = "comment"
    TAGS: str = "tags"
    LOCATION: str = "location"
    ACTORS: str = "actors"

    # Sound
    SOUND_TYPE: str = "sound_type"


class EpisodeDataKeys:
    """Klucze danych odcinków (rozszerzenie EpisodeMetadataKeys)."""

    # Episode info
    EPISODE_INFO: str = "episode_info"
    EPISODE_METADATA: str = "episode_metadata"
    EPISODE_ID: str = "episode_id"

    # Episode details (verify if in EpisodeMetadataKeys)
    SEASON: str = "season"
    EPISODE_NUMBER: str = "episode_number"
    TITLE: str = "title"
    PREMIERE_DATE: str = "premiere_date"
    VIEWERSHIP: str = "viewership"

    # Media
    VIDEO_PATH: str = "video_path"


class EmbeddingKeys:
    """Klucze związane z embeddingami."""

    # Embeddings
    EMBEDDING: str = "embedding"
    TEXT_EMBEDDING: str = "text_embedding"
    VIDEO_EMBEDDING: str = "video_embedding"
    TITLE_EMBEDDING: str = "title_embedding"

    # Metadata
    EMBEDDING_DIMENSION: str = "embedding_dimension"
    EMBEDDING_ID: str = "embedding_id"


class FrameProcessingKeys:
    """Klucze przetwarzania ramek wideo."""

    # Frames
    FRAMES: str = "frames"
    FRAME_NUMBER: str = "frame_number"
    FRAME_PATH: str = "frame_path"

    # Characters
    CHARACTERS: str = "characters"
    CHARACTER_APPEARANCES: str = "character_appearances"
    NAME: str = "name"
    CONFIDENCE: str = "confidence"
    BBOX: str = "bbox"

    # Emotions
    EMOTION: str = "emotion"
    LABEL: str = "label"

    # Objects
    DETECTED_OBJECTS: str = "detected_objects"
    DETECTIONS: str = "detections"
    DETECTION_COUNT: str = "detection_count"
    CLASS: str = "class"
    CLASS_NAME: str = "class_name"

    # Scene
    SCENE_INFO: str = "scene_info"
    SCENE_NUMBER: str = "scene_number"
    SCENE_TIMESTAMPS: str = "scene_timestamps"
    SCENE_START_TIME: str = "scene_start_time"
    SCENE_END_TIME: str = "scene_end_time"

    # Hashing
    PERCEPTUAL_HASH: str = "perceptual_hash"


class HttpResponseKeys:
    """Klucze HTTP response."""

    # Headers
    PRAGMA: str = "Pragma"
    EXPIRES: str = "Expires"
    CACHE_CONTROL: str = "Cache-Control"

    # Values
    NO_CACHE: str = "no-cache"
    ZERO: str = "0"


class DatabaseConnectionKeys:
    """Klucze konfiguracji połączenia z bazą danych."""

    HOST: str = "host"
    PORT: str = "port"
    DATABASE: str = "database"
    USER: str = "user"
    PASSWORD: str = "password"
    SERVER_SETTINGS: str = "server_settings"
    SEARCH_PATH: str = "search_path"


class StartCommandAliases:
    """Aliasy komend dla /start."""

    # Polish
    LISTA: str = "lista"
    WSZYSTKO: str = "wszystko"
    WYSZUKIWANIE: str = "wyszukiwanie"
    EDYCJA: str = "edycja"
    ZARZADZANIE: str = "zarzadzanie"
    RAPORTOWANIE: str = "raportowanie"
    SUBSKRYPCJE: str = "subskrypcje"
    SKROTY: str = "skroty"

    # English
    LIST: str = "list"
    ALL: str = "all"
    SEARCH: str = "search"
    EDIT: str = "edit"
    MANAGEMENT: str = "management"
    REPORTING: str = "reporting"
    SUBSCRIPTIONS: str = "subscriptions"
    SHORTCUTS: str = "shortcuts"

    # Short
    L: str = "l"
    A: str = "a"
    S: str = "s"
    E: str = "e"
    M: str = "m"
    R: str = "r"
    SUB: str = "sub"
    SH: str = "sh"
```

---

### Krok 2: Utworzyć nowe klasy w `preprocessor/utils/constants.py`

```python
# preprocessor/utils/constants.py

class ConfigKeys:
    """Klucze konfiguracji processorów."""

    # Core config
    SERIES_NAME: str = "series_name"
    NAME: str = "name"  # alias for series_name
    EPISODES_INFO_JSON: str = "episodes_info_json"
    STATE_MANAGER: str = "state_manager"

    # Input directories
    VIDEOS: str = "videos"
    TRANSCODED_VIDEOS: str = "transcoded_videos"
    TRANSCRIPTION_JSONS: str = "transcription_jsons"
    FRAMES_DIR: str = "frames_dir"
    OUTPUT_FRAMES: str = "output_frames"
    CHARACTERS_DIR: str = "characters_dir"
    CHARACTERS_JSON: str = "characters_json"

    # Output directories
    OUTPUT_DIR: str = "output_dir"
    EMBEDDINGS_DIR: str = "embeddings_dir"
    SCENE_TIMESTAMPS_DIR: str = "scene_timestamps_dir"
    CHARACTER_DETECTIONS_DIR: str = "character_detections_dir"
    OBJECT_DETECTIONS_DIR: str = "object_detections_dir"
    IMAGE_HASHES_DIR: str = "image_hashes_dir"
    ELASTIC_DOCUMENTS_DIR: str = "elastic_documents_dir"
    SOURCE_DIR: str = "source_dir"

    # Processing parameters
    DEVICE: str = "device"
    MODEL: str = "model"
    MODEL_REVISION: str = "model_revision"
    BATCH_SIZE: str = "batch_size"
    RESOLUTION: str = "resolution"
    CODEC: str = "codec"
    LANGUAGE: str = "language"

    # Embedding parameters
    SEGMENTS_PER_EMBEDDING: str = "segments_per_embedding"
    TEXT_SENTENCES_PER_CHUNK: str = "text_sentences_per_chunk"
    TEXT_CHUNK_OVERLAP: str = "text_chunk_overlap"
    GENERATE_TEXT: str = "generate_text"
    GENERATE_VIDEO: str = "generate_video"
    GENERATE_EPISODE_NAMES: str = "generate_episode_names"
    GENERATE_FULL_EPISODE: str = "generate_full_episode"
    GENERATE_SOUND_EVENTS: str = "generate_sound_events"

    # Scene detection
    THRESHOLD: str = "threshold"
    MIN_SCENE_LEN: str = "min_scene_len"

    # Character processing
    SIMILARITY_THRESHOLD: str = "similarity_threshold"
    INTERACTIVE: str = "interactive"
    IMAGES_PER_CHARACTER: str = "images_per_character"
    SEARCH_MODE: str = "search_mode"

    # Transcription
    TRANSCRIPTION_MODE: str = "transcription_mode"
    API_KEY: str = "api_key"
    MODEL_ID: str = "model_id"
    LANGUAGE_CODE: str = "language_code"
    DIARIZE: str = "diarize"

    # Archive generation
    FORCE_REGENERATE: str = "force_regenerate"
    ALLOW_PARTIAL: str = "allow_partial"
    SEASON_FILTER: str = "season_filter"
    EPISODE_FILTER: str = "episode_filter"

    # Elasticsearch
    DRY_RUN: str = "dry_run"
    APPEND: str = "append"

    # Scraping
    URLS: str = "urls"
    OUTPUT_FILE: str = "output_file"
    HEADLESS: str = "headless"
    MERGE_SOURCES: str = "merge_sources"
    PARSER_MODE: str = "parser_mode"

    # Runtime
    RAMDISK_PATH: str = "ramdisk_path"
    PROGRESS_TRACKER: str = "progress_tracker"

    # Format
    FORMAT_TYPE: str = "format_type"


class ClickContextKeys:
    """Klucze kontekstu Click CLI."""

    SHOW_DEFAULT: str = "show_default"
    CONTEXT_SETTINGS: str = "context_settings"


# Predefiniowany kontekst Click
CLICK_DEFAULT_CONTEXT: Dict[str, bool] = {
    ClickContextKeys.SHOW_DEFAULT: True,
}


class ProcessingMetadataKeys:
    """Klucze metadanych przetwarzania."""

    # Metadata structure
    METADATA: str = "metadata"
    EPISODE_INFO: str = "episode_info"
    EPISODE_DIR: str = "episode_dir"
    BASE_NAME: str = "base_name"
    CHAR_NAME: str = "char_name"

    # File metadata
    FILE: str = "file"
    SIZE_MB: str = "size_mb"
    WIDTH: str = "width"
    HEIGHT: str = "height"
    DURATION: str = "duration"
    CODEC: str = "codec"

    # Processing state
    MISSING_OUTPUTS: str = "missing_outputs"
    ADDITIONAL_STATISTICS: str = "additional_statistics"
    STATISTICS: str = "statistics"
    TOTAL_FRAMES: str = "total_frames"

    # Detection metadata
    DETECTION_IDX: str = "detection_idx"
    CHAR_IDX: str = "char_idx"


class CharacterReferenceKeys:
    """Klucze dla referencji postaci."""

    # Structure
    CHARACTERS: str = "characters"
    NAME: str = "name"
    SOURCES: str = "sources"

    # Scraping
    URL: str = "url"
    MARKDOWN: str = "markdown"

    # Images
    IMAGE: str = "image"
    THUMBNAIL: str = "thumbnail"
    ORIGINAL: str = "original"

    # Detection stats
    CHARACTER_NAME: str = "character_name"
    SOURCE_IMAGES: str = "source_images"
    PROCESSED_AT: str = "processed_at"
    PROCESSING_PARAMS: str = "processing_params"
    FACE_MODEL: str = "face_model"
    NORMALIZED_FACE_SIZE: str = "normalized_face_size"

    DETECTION_STATS: str = "detection_stats"
    TOTAL_FACES_DETECTED: str = "total_faces_detected"
    CANDIDATES_FOUND: str = "candidates_found"
    SELECTION_METHOD: str = "selection_method"
    SELECTED_FACE_INDICES: str = "selected_face_indices"
    AVERAGE_SIMILARITY: str = "average_similarity"
    FACE_VECTOR_DIM: str = "face_vector_dim"


class StateManagerKeys:
    """Klucze dla state managera."""

    SERIES_NAME: str = "series_name"
    STARTED_AT: str = "started_at"
    LAST_CHECKPOINT: str = "last_checkpoint"
    COMPLETED_STEPS: str = "completed_steps"
    IN_PROGRESS: str = "in_progress"


class ValidationKeys:
    """Klucze dla validacji."""

    STATS: str = "stats"

    # JSON validation
    EPISODES_JSON_VALID: str = "episodes_json_valid"
    CHARACTERS_JSON_VALID: str = "characters_json_valid"

    # Character validation
    CHARACTER_FOLDERS_COUNT: str = "character_folders_count"
    CHARACTER_IMAGES_COUNT: str = "character_images_count"
    INVALID_CHARACTER_IMAGES: str = "invalid_character_images"

    # Processing validation
    PROCESSING_METADATA_FILES: str = "processing_metadata_files"

    # File counts
    TRANSCRIPTION_FILES_COUNT: str = "transcription_files_count"
    TRANSCRIPTION_FILES: str = "transcription_files"
    TRANSCODED_VIDEOS_COUNT: str = "transcoded_videos_count"
    TRANSCODED_VIDEOS_TOTAL_SIZE_MB: str = "transcoded_videos_total_size_mb"
    PROCESSED_EPISODES_COUNT: str = "processed_episodes_count"
    TOTAL_FRAMES_EXTRACTED: str = "total_frames_extracted"
    TEXT_EMBEDDING_FILES_COUNT: str = "text_embedding_files_count"
    VIDEO_EMBEDDING_FILES_COUNT: str = "video_embedding_files_count"
    IMAGE_HASH_FILES_COUNT: str = "image_hash_files_count"

    # Elasticsearch
    ELASTIC_DOCUMENTS: str = "elastic_documents"


class PromptSystemKeys:
    """Klucze dla systemu promptów LLM."""

    ROLE: str = "role"
    USER: str = "user"
    ASSISTANT: str = "assistant"
    SYSTEM: str = "system"

    CONTENT: str = "content"
    TEXT: str = "text"
    IMAGE: str = "image"
    TYPE: str = "type"


class TranscriptionKeys:
    """Klucze specyficzne dla transkrypcji."""

    LANGUAGE: str = "language"
    TEMPERATURE: str = "temperature"
    SPEAKER_ID: str = "speaker_id"
    SOUND_TYPE: str = "sound_type"


class FilePatternKeys:
    """Klucze wzorców plików (rozszerzenie FILE_SUFFIXES)."""

    # Suffixes (verify against existing FILE_SUFFIXES)
    SEGMENTED: str = "segmented"
    SIMPLE: str = "simple"
    SOUND_EVENTS: str = "sound_events"
    CLEAN: str = "clean"
    CLEAN_ALT: str = "clean_alt"
    TEXT_SEGMENTS: str = "text_segments"

    # Extensions (verify against existing FILE_EXTENSIONS)
    JSON: str = "json"
    TXT: str = "txt"
    SRT: str = "srt"


class ElasticSearchCountKeys:
    """Klucze dla zliczania dokumentów ES."""

    COUNT: str = "count"
    SEGMENTS: str = "segments"
    TEXT_EMBEDDINGS: str = "text_embeddings"
    VIDEO_EMBEDDINGS: str = "video_embeddings"
    EPISODE_NAMES: str = "episode_names"
```

---

### Krok 3: Przykłady refaktoryzacji

#### Przykład 1: Elasticsearch queries

**Przed:**
```python
# bot/search/elastic_search_manager.py
query = {
    "bool": {
        "must": [
            {"term": {"episode_metadata.season": season}}
        ]
    }
}
result = await es.search(index="ranczo_segments", body={"query": query})
hits = result["hits"]["hits"]
for hit in hits:
    text = hit["_source"]["text"]
```

**Po:**
```python
from bot.utils.constants import (
    ElasticsearchKeys as ESK,
    ElasticsearchIndexNames as ESIN,
    SegmentDataKeys as SDK,
    EpisodeDataKeys as EDK,
)

query = {
    ESK.BOOL: {
        ESK.MUST: [
            {ESK.TERM: {f"{EDK.EPISODE_METADATA}.{EDK.SEASON}": season}}
        ]
    }
}
result = await es.search(
    index=ESIN.SEGMENTS,
    body={ESK.QUERY: query}
)
hits = result[ESK.HITS][ESK.HITS]
for hit in hits:
    text = hit[ESK.SOURCE][SDK.TEXT]
```

#### Przykład 2: JWT token

**Przed:**
```python
# bot/adapters/rest/auth/jwt_token.py
payload = {
    "user_id": user_id,
    "username": username,
    "full_name": full_name,
    "iat": now_utc.timestamp(),
    "exp": expire.timestamp(),
}
```

**Po:**
```python
from bot.utils.constants import JwtPayloadKeys as JPK

payload = {
    JPK.USER_ID: user_id,
    JPK.USERNAME: username,
    JPK.FULL_NAME: full_name,
    JPK.IAT: now_utc.timestamp(),
    JPK.EXP: expire.timestamp(),
}
```

#### Przykład 3: Response data

**Przed:**
```python
# bot/handlers/not_sending_videos/search_handler.py
await self.reply(
    response_text,
    data={
        "quote": quote,
        "results": segments,
    }
)
```

**Po:**
```python
from bot.utils.constants import ResponseDataKeys as RDK

await self.reply(
    response_text,
    data={
        RDK.QUOTE: quote,
        RDK.RESULTS: segments,
    }
)
```

#### Przykład 4: Config dictionary

**Przed:**
```python
# preprocessor/cli/commands/export_frames.py
config = {
    "transcoded_videos": transcoded_videos,
    "scene_timestamps_dir": scene_timestamps_dir,
    "output_frames": output_frames,
    "resolution": res,
    "series_name": name,
    "episodes_info_json": episodes_info_json,
    "state_manager": state_manager,
}
```

**Po:**
```python
from preprocessor.utils.constants import ConfigKeys as CK

config = {
    CK.TRANSCODED_VIDEOS: transcoded_videos,
    CK.SCENE_TIMESTAMPS_DIR: scene_timestamps_dir,
    CK.OUTPUT_FRAMES: output_frames,
    CK.RESOLUTION: res,
    CK.SERIES_NAME: name,
    CK.EPISODES_INFO_JSON: episodes_info_json,
    CK.STATE_MANAGER: state_manager,
}
```

#### Przykład 5: Click commands

**Przed:**
```python
# preprocessor/cli/commands/export_frames.py
@click.command(context_settings={"show_default": True})
```

**Po:**
```python
from preprocessor.utils.constants import CLICK_DEFAULT_CONTEXT

@click.command(context_settings=CLICK_DEFAULT_CONTEXT)
```

---

## LISTA PLIKÓW DO REFAKTORYZACJI (TOP PRIORITY)

### Bot (wysokie ryzyko)
1. ✅ `bot/search/elastic_search_manager.py` - 60+ raw stringów ES
2. ✅ `bot/adapters/rest/auth/jwt_token.py` - JWT keys
3. ✅ `bot/adapters/rest/rest_message.py` - user data keys
4. ✅ `bot/platforms/rest_runner.py` - API, auth, cookies
5. ✅ `bot/handlers/administration/start_handler.py` - command aliases
6. ✅ `bot/handlers/not_sending_videos/*.py` - response data keys
7. ✅ `bot/handlers/sending_videos/*.py` - video operation keys
8. ✅ `bot/search/transcription_finder.py` - segment/episode keys
9. ✅ `bot/services/reindex/reindex_service.py` - ES index names
10. ✅ `bot/database/database_manager.py` - connection keys

### Preprocessor (wysokie ryzyko)
1. ✅ `preprocessor/search/elastic_manager.py` - ES mappings (150+ raw stringów)
2. ✅ `preprocessor/indexing/elastic_document_generator.py` - document generation
3. ✅ `preprocessor/embeddings/embedding_generator.py` - embedding keys
4. ✅ `preprocessor/cli/commands/search.py` - ES queries
5. ✅ `preprocessor/cli/commands/*.py` - wszystkie (config keys)
6. ✅ `preprocessor/cli/pipeline/steps.py` - pipeline config
7. ✅ `preprocessor/core/base_processor.py` - processor args
8. ✅ `preprocessor/video/frame_subprocessors.py` - frame keys
9. ✅ `preprocessor/characters/detector.py` - detection keys
10. ✅ `preprocessor/transcription/*.py` - transcription keys

---

## CHECKLIST REFAKTORYZACJI

### Dla każdego pliku:

- [ ] Zidentyfikować wszystkie raw stringi
- [ ] Sprawdzić czy nie są już w constants.py
- [ ] Pogrupować stringi według kontekstu
- [ ] Wybrać odpowiednią klasę stałych
- [ ] Dodać import na górze pliku
- [ ] Zastąpić raw stringi stałymi
- [ ] Uruchomić testy
- [ ] Zweryfikować czy kod działa poprawnie

### Dla każdej nowej klasy stałych:

- [ ] Dodać docstring z opisem
- [ ] Użyć type hints (`: str =`)
- [ ] Posortować alfabetycznie lub logicznie
- [ ] Dodać komentarze dla grup kluczy
- [ ] Zweryfikować czy nie ma duplikatów z innymi klasami

---

## TESTY

Po każdej refaktoryzacji uruchomić:

```bash
# Bot tests
pytest bot/tests/ -v

# Preprocessor tests (jeśli istnieją)
pytest preprocessor/tests/ -v

# Linter
ruff check bot/ preprocessor/
mypy bot/ preprocessor/
```

---

## SZACOWANY CZAS

| Faza | Czas | Pliki | Stringi |
|------|------|-------|---------|
| Utworzenie klas stałych | 2h | 2 | ~150 |
| Refaktoryzacja bot/ | 8h | ~15 | ~120 |
| Refaktoryzacja preprocessor/ | 16h | ~30 | ~200 |
| Testy i weryfikacja | 4h | wszystkie | wszystkie |
| **RAZEM** | **30h** | **~47** | **~470** |

---

## METRYKI POSTĘPU

Sprawdzić postęp za pomocą:

```bash
# Policzyć pozostałe raw stringi
python3 analyze_raw_strings.py | grep "Stringi występujące 3+ razy:"

# Sprawdzić konkretny plik
grep -o '\.get\s*(\s*["'\'']\w\+["'\'']' <plik>.py | wc -l
```

---

## UWAGI KOŃCOWE

1. **Nie łączyć zbyt wielu plików w jednym commicie** - łatwiej wycofać zmiany jeśli coś pójdzie nie tak
2. **Zawsze uruchamiać testy po każdej grupie zmian**
3. **Priorytet: najpierw bot/, potem preprocessor/** - bot jest krytyczny dla działania systemu
4. **W razie wątpliwości - pytać użytkownika** przed dużymi zmianami
5. **Dokumentować zmiany** - aktualizować ten dokument jeśli coś się zmienia

---

**Status:** ✅ Gotowe do implementacji
**Next steps:** Rozpocząć od utworzenia klas w `bot/utils/constants.py`

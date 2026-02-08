# RAPORT ANALIZY RAW STRINGÓW - GŁĘBOKA ANALIZA
**Data:** 2026-02-08
**Zakres:** bot/, preprocessor/
**Wykluczono:** pliki constants.py, testy, __pycache__

---

## PODSUMOWANIE WYKONAWCZE

**Znalezione stringi:**
- Całkowita liczba unikalnych stringów: **600**
- Stringi występujące 3+ razy: **226** ← WYSOKIE RYZYKO
- Stringi występujące 2 razy: **94** ← ŚREDNIE RYZYKO
- Stringi występujące 1 raz: **280** ← NISKIE RYZYKO

---

## KATEGORIA A - WYSOKIE RYZYKO (MUST FIX)
**Klucze powtarzające się 3+ razy - MUSZĄ być wyciągnięte jako stałe**

### 1. **ElasticsearchKeys** (klucze Elasticsearch API)
**Priorytet: KRYTYCZNY**

```python
class ElasticsearchKeys:
    # Mapping keys
    TYPE = "type"  # 177 wystąpień
    PROPERTIES = "properties"  # 30 wystąpień
    MAPPINGS = "mappings"  # ~20 wystąpień

    # Response keys
    HITS = "hits"  # 18 wystąpień
    SOURCE = "_source"  # ~15 wystąpień
    INDEX = "_index"  # ~10 wystąpień
    ID = "_id"  # ~10 wystąpień

    # Query keys
    BOOL = "bool"  # ~25 wystąpień
    MUST = "must"  # ~20 wystąpień
    FILTER = "filter"  # ~20 wystąpień
    TERM = "term"  # 31 wystąpień
    NESTED = "nested"  # 12 wystąpień
    PATH = "path"  # ~15 wystąpień
    QUERY = "query"  # ~25 wystąpień
    FIELD = "field"  # ~20 wystąpień

    # Search types
    MULTI_MATCH = "multi_match"  # ~10 wystąpień
    RANGE = "range"  # ~10 wystąpień

    # Aggregations
    AGGS = "aggs"  # ~10 wystąpień
    AGGREGATIONS = "aggregations"  # ~10 wystąpień
    BUCKETS = "buckets"  # ~8 wystąpień

    # Sorting
    ORDER = "order"  # ~8 wystąpień
```

**Lokalizacje:**
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/bot/search/elastic_search_manager.py`
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/search/elastic_manager.py`
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/indexing/elasticsearch.py`
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/indexing/elastic_document_generator.py`
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/cli/commands/search.py`

---

### 2. **SegmentDataKeys** (klucze danych segmentów - ROZSZERZENIE SegmentKeys)
**Priorytet: KRYTYCZNY**

```python
class SegmentDataKeys:
    # Podstawowe (już są w SegmentKeys, ale warto zweryfikować)
    TEXT = "text"  # 83 wystąpienia
    START = "start"  # 41 wystąpień
    END = "end"  # 41 wystąpień
    SEGMENTS = "segments"  # 44 wystąpienia

    # Segment metadata
    WORDS = "words"  # 33 wystąpienia
    SPEAKER = "speaker"  # 12 wystąpień
    SEGMENT_RANGE = "segment_range"  # 12 wystąpień

    # Timestamps
    START_TIME = "start_time"  # 14 wystąpień
    END_TIME = "end_time"  # 12 wystąpień

    # Other
    SEEK = "seek"  # ~10 wystąpień
    AUTHOR = "author"  # ~8 wystąpień
    COMMENT = "comment"  # ~8 wystąpień
    TAGS = "tags"  # ~8 wystąpień
    LOCATION = "location"  # ~8 wystąpień
    ACTORS = "actors"  # ~8 wystąpień
    TIMESTAMP = "timestamp"  # ~8 wystąpień
```

**Lokalizacje:**
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/bot/search/elastic_search_manager.py`
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/embeddings/embedding_generator.py`
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/indexing/elastic_document_generator.py`

---

### 3. **EpisodeDataKeys** (klucze danych odcinków - ROZSZERZENIE EpisodeMetadataKeys)
**Priorytet: KRYTYCZNY**

```python
class EpisodeDataKeys:
    # Już istnieją w EpisodeMetadataKeys, ale należy zweryfikować
    EPISODE_INFO = "episode_info"  # 60 wystąpień
    SEASON = "season"  # 31 wystąpień
    EPISODE_NUMBER = "episode_number"  # 30 wystąpień
    TITLE = "title"  # 23 wystąpienia
    PREMIERE_DATE = "premiere_date"  # 16 wystąpień
    VIEWERSHIP = "viewership"  # 14 wystąpień

    # Dodatkowe
    EPISODE_ID = "episode_id"  # 25 wystąpień
    EPISODE_METADATA = "episode_metadata"  # 16 wystąpień
    VIDEO_PATH = "video_path"  # 27 wystąpień
```

**Lokalizacje:**
- Wszystkie procesory w `preprocessor/`
- Wszystkie handlery w `bot/handlers/`

---

### 4. **ConfigKeys** (klucze konfiguracji)
**Priorytet: WYSOKI**

```python
class ConfigKeys:
    # Processing config
    SERIES_NAME = "series_name"  # 53 wystąpienia
    EPISODES_INFO_JSON = "episodes_info_json"  # 49 wystąpień
    STATE_MANAGER = "state_manager"  # 22 wystąpienia

    # Input/Output
    VIDEOS = "videos"  # 17 wystąpień
    OUTPUT_DIR = "output_dir"  # 26 wystąpień
    TRANSCRIPTION_JSONS = "transcription_jsons"  # 17 wystąpień
    FRAMES_DIR = "frames_dir"  # ~15 wystąpień
    TRANSCODED_VIDEOS = "transcoded_videos"  # ~12 wystąpień

    # Processing params
    DEVICE = "device"  # 15 wystąpień
    NAME = "name"  # 31 wystąpienie (używane jako alias dla series_name)
    MODEL = "model"  # ~12 wystąpień
    BATCH_SIZE = "batch_size"  # ~10 wystąpień

    # CLI specific
    SHOW_DEFAULT = "show_default"  # 18 wystąpień (Click context settings)
    CONTEXT_SETTINGS = "context_settings"  # ~18 wystąpień
```

**Lokalizacje:**
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/core/base_processor.py`
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/cli/commands/` (wszystkie pliki)
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/cli/pipeline/steps.py`

---

### 5. **EmbeddingKeys** (klucze embeddingów)
**Priorytet: WYSOKI**

```python
class EmbeddingKeys:
    EMBEDDING = "embedding"  # 14 wystąpień
    TEXT_EMBEDDING = "text_embedding"  # ~10 wystąpień
    VIDEO_EMBEDDING = "video_embedding"  # ~10 wystąpień
    TITLE_EMBEDDING = "title_embedding"  # ~8 wystąpień

    # Metadata
    EMBEDDING_DIMENSION = "embedding_dimension"  # ~10 wystąpień
    EMBEDDING_ID = "embedding_id"  # ~8 wystąpień

    # Already in constants (verify)
    EPISODE_METADATA = "episode_metadata"  # używane w embedding_generator.py
```

**Lokalizacje:**
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/embeddings/embedding_generator.py`
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/indexing/elastic_document_generator.py`

---

### 6. **JwtPayloadKeys** (JUŻ ISTNIEJE - zweryfikować kompletność)
**Priorytet: WERYFIKACJA**

```python
# SPRAWDŹ czy te klucze są już w JwtPayloadKeys:
class JwtPayloadKeys:
    USER_ID = "user_id"  # ~15 wystąpień
    USERNAME = "username"  # ~15 wystąpień
    FULL_NAME = "full_name"  # ~15 wystąpień

    # JWT standard claims
    IAT = "iat"  # issued at - ~8 wystąpień
    EXP = "exp"  # expiration - ~8 wystąpień
    ISS = "iss"  # issuer - ~8 wystąpień
    AUD = "aud"  # audience - ~8 wystąpień

    # Custom
    REQUIRE = "require"  # ~5 wystąpień (validation)
```

**Lokalizacje:**
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/bot/adapters/rest/auth/jwt_token.py`
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/bot/adapters/rest/rest_message.py`
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/bot/tests/` (wiele plików)

---

### 7. **ResponseDataKeys** (klucze odpowiedzi API)
**Priorytet: WYSOKI**

```python
class ResponseDataKeys:
    # Response structure
    STATUS = "status"  # ~10 wystąpień
    MESSAGE = "message"  # ~15 wystąpień
    DATA = "data"  # ~10 wystąpień
    CONTENT = "content"  # ~10 wystąpień

    # Response types (już w ResponseType?)
    TYPE = "type"  # verify if different from ElasticsearchKeys.TYPE

    # Data fields
    QUOTE = "quote"  # ~8 wystąpień
    RESULTS = "results"  # ~8 wystąpień
    SEGMENT = "segment"  # ~8 wystąpień
    CLIPS = "clips"  # ~8 wystąpień
    SEASON_INFO = "season_info"  # ~8 wystąpień
    EPISODES = "episodes"  # ~8 wystąpień
    WHITELIST = "whitelist"  # ~5 wystąpień
    MODERATORS = "moderators"  # ~5 wystąpień
    ADMINS = "admins"  # ~5 wystąpień
    KEYS = "keys"  # ~5 wystąpień

    # Subscription
    DAYS = "days"  # ~6 wystąpień
    KEY = "key"  # ~6 wystąpień
    SUBSCRIPTION_END = "subscription_end"  # ~8 wystąpień
    DAYS_REMAINING = "days_remaining"  # ~5 wystąpień
```

**Lokalizacje:**
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/bot/handlers/` (wszystkie handlery)
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/bot/adapters/rest/rest_responder.py`

---

### 8. **FrameProcessingKeys** (klucze przetwarzania ramek)
**Priorytet: ŚREDNI-WYSOKI**

```python
class FrameProcessingKeys:
    FRAMES = "frames"  # 15 wystąpień
    FRAME_NUMBER = "frame_number"  # ~12 wystąpień
    FRAME_PATH = "frame_path"  # ~12 wystąpień

    # Detection results
    CHARACTERS = "characters"  # ~12 wystąpień
    CHARACTER_APPEARANCES = "character_appearances"  # ~15 wystąpień
    DETECTED_OBJECTS = "detected_objects"  # ~12 wystąpień
    DETECTIONS = "detections"  # ~12 wystąpień
    DETECTION_COUNT = "detection_count"  # ~8 wystąpień

    # Character data
    CONFIDENCE = "confidence"  # ~12 wystąpień
    BBOX = "bbox"  # ~10 wystąpień
    EMOTION = "emotion"  # ~10 wystąpień
    LABEL = "label"  # ~10 wystąpień

    # Scene data
    SCENE_INFO = "scene_info"  # ~10 wystąpień
    SCENE_NUMBER = "scene_number"  # ~8 wystąpień
    SCENE_TIMESTAMPS = "scene_timestamps"  # ~8 wystąpień
```

**Lokalizacje:**
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/video/frame_subprocessors.py`
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/video/frame_exporter.py`
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/characters/detector.py`

---

### 9. **TranscriptionKeys** (klucze transkrypcji)
**Priorytet: ŚREDNI-WYSOKI**

```python
class TranscriptionKeys:
    # Already covered by SegmentDataKeys, but specific to transcription
    LANGUAGE = "language"  # ~10 wystąpień
    TEMPERATURE = "temperature"  # ~8 wystąpień

    # Whisper specific
    SPEAKER_ID = "speaker_id"  # ~8 wystąpień

    # Sound separation
    SOUND_TYPE = "sound_type"  # ~8 wystąpień
    SOUND = "sound"  # ~6 wystąpień
```

**Lokalizacje:**
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/transcription/` (wiele plików)

---

### 10. **CommandAliasKeys** (aliasy komend startowych)
**Priorytet: NISKI-ŚREDNI**

```python
class StartCommandAliases:
    # Polish
    LISTA = "lista"
    WSZYSTKO = "wszystko"
    WYSZUKIWANIE = "wyszukiwanie"
    EDYCJA = "edycja"
    ZARZADZANIE = "zarzadzanie"
    RAPORTOWANIE = "raportowanie"
    SUBSKRYPCJE = "subskrypcje"
    SKROTY = "skroty"

    # English
    LIST = "list"
    ALL = "all"
    SEARCH = "search"
    EDIT = "edit"
    MANAGEMENT = "management"
    REPORTING = "reporting"
    SUBSCRIPTIONS = "subscriptions"
    SHORTCUTS = "shortcuts"

    # Short
    L = "l"
    A = "a"
    S = "s"
    E = "e"
    M = "m"
    R = "r"
    SUB = "sub"
    SH = "sh"
```

**Lokalizacje:**
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/bot/handlers/administration/start_handler.py`

---

### 11. **HttpResponseKeys** (HTTP i cookies)
**Priorytet: ŚREDNI**

```python
class HttpResponseKeys:
    # Headers
    PRAGMA = "Pragma"  # ~5 wystąpień
    EXPIRES = "Expires"  # ~5 wystąpień
    CACHE_CONTROL = "Cache-Control"  # potential

    # Status
    NO_CACHE = "no-cache"  # ~5 wystąpień

    # Values
    ZERO = "0"  # used for Expires
```

**Lokalizacje:**
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/bot/platforms/rest_runner.py`

---

### 12. **ProcessingMetadataKeys** (metadata przetwarzania)
**Priorytet: ŚREDNI**

```python
class ProcessingMetadataKeys:
    # Metadata
    METADATA = "metadata"  # ~15 wystąpień
    CHAR_NAME = "char_name"  # ~8 wystąpień
    BASE_NAME = "base_name"  # ~8 wystąpień
    EPISODE_DIR = "episode_dir"  # ~8 wystąpień

    # File info
    FILE = "file"  # ~10 wystąpień
    SIZE_MB = "size_mb"  # ~8 wystąpień
    WIDTH = "width"  # ~8 wystąpień
    HEIGHT = "height"  # ~8 wystąpień
    DURATION = "duration"  # ~8 wystąpień
    CODEC = "codec"  # ~8 wystąpień

    # Processing state
    MISSING_OUTPUTS = "missing_outputs"  # ~5 wystąpień
    ADDITIONAL_STATISTICS = "additional_statistics"  # ~5 wystąpień
```

**Lokalizacje:**
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/core/processing_metadata.py`
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/core/base_processor.py`

---

### 13. **ElasticsearchIndexNames** (nazwy indeksów - jako stałe, nie TypedDict)
**Priorytet: ŚREDNI**

```python
class ElasticsearchIndexNames:
    SEGMENTS = "ranczo_segments"
    TEXT_EMBEDDINGS = "ranczo_text_embeddings"
    VIDEO_FRAMES = "ranczo_video_frames"
    EPISODE_NAMES = "ranczo_episode_names"
    FULL_EPISODE_EMBEDDINGS = "ranczo_full_episode_embeddings"
    SOUND_EVENTS = "ranczo_sound_events"
    SOUND_EVENT_EMBEDDINGS = "ranczo_sound_event_embeddings"

    # Index types (for mapping)
    TEXT_SEGMENTS = "text_segments"
    VIDEO_FRAMES_TYPE = "video_frames"
```

**Lokalizacje:**
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/cli/commands/search.py`
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/bot/services/reindex/reindex_service.py`

---

## KATEGORIA B - ŚREDNIE RYZYKO (SHOULD FIX)
**Klucze powtarzające się 2 razy - POWINNY być stałymi**

### Analiza wybranych przypadków:

#### **DatabaseConnectionKeys**
```python
class DatabaseConnectionKeys:
    HOST = "host"
    PORT = "port"
    DATABASE = "database"
    USER = "user"
    PASSWORD = "password"
    SERVER_SETTINGS = "server_settings"
    SEARCH_PATH = "search_path"
```

**Lokalizacje:** `/mnt/c/GIT_REPO/RANCZO_KLIPY/bot/database/database_manager.py:55-60`

---

#### **ValidationKeys**
```python
class ValidationKeys:
    STATS = "stats"
    EPISODES_JSON_VALID = "episodes_json_valid"
    CHARACTERS_JSON_VALID = "characters_json_valid"
    CHARACTER_FOLDERS_COUNT = "character_folders_count"
    CHARACTER_IMAGES_COUNT = "character_images_count"
    INVALID_CHARACTER_IMAGES = "invalid_character_images"
```

**Lokalizacje:** `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/validation/`

---

#### **StateManagerKeys**
```python
class StateManagerKeys:
    SERIES_NAME = "series_name"
    STARTED_AT = "started_at"
    LAST_CHECKPOINT = "last_checkpoint"
    COMPLETED_STEPS = "completed_steps"
    IN_PROGRESS = "in_progress"
```

**Lokalizacje:** `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/core/state_manager.py`

---

#### **CharacterReferenceKeys**
```python
class CharacterReferenceKeys:
    CHARACTERS = "characters"
    SOURCES = "sources"
    URL = "url"
    MARKDOWN = "markdown"
    IMAGE = "image"
    THUMBNAIL = "thumbnail"
    ORIGINAL = "original"

    # Detection
    SELECTION_METHOD = "selection_method"
    TOTAL_FACES_DETECTED = "total_faces_detected"
    CANDIDATES_FOUND = "candidates_found"
    AVERAGE_SIMILARITY = "average_similarity"
    DETECTION_STATS = "detection_stats"
```

**Lokalizacje:**
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/characters/reference_processor.py`
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/characters/reference_downloader.py`

---

#### **PromptSystemKeys** (dla LLM promptów)
```python
class PromptSystemKeys:
    ROLE = "role"
    USER = "user"
    CONTENT = "content"
    TEXT = "text"
    IMAGE = "image"
```

**Lokalizacje:** `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/cli/commands/search.py`

---

#### **ElevenLabsKeys** (dla API ElevenLabs)
```python
class ElevenLabsKeys:
    API_KEY = "api_key"
    MODEL_ID = "model_id"
    LANGUAGE_CODE = "language_code"
    DIARIZE = "diarize"
```

**Lokalizacje:**
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/cli/commands/transcribe_elevenlabs.py`
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/cli/pipeline/steps.py`

---

## KATEGORIA C - NISKIE RYZYKO (COULD FIX)
**Stringi występujące 1 raz - opcjonalnie**

280 stringów występuje tylko raz. Większość to:
- Komunikaty użytkownika (nie wymagają stałych)
- Konfiguracja bibliotek zewnętrznych (może zostać)
- Jednorazowe klucze specyficzne dla funkcji (nie krytyczne)

**Zalecenie:** Przeanalizować indywidualnie tylko te, które są krytyczne dla bezpieczeństwa lub API.

---

## PLAN IMPLEMENTACJI

### Faza 1: KRYTYCZNE (Week 1)
1. ✅ Utworzyć `ElasticsearchKeys` w `bot/utils/constants.py`
2. ✅ Rozszerzyć `SegmentDataKeys` lub utworzyć nową klasę
3. ✅ Zweryfikować i uzupełnić `JwtPayloadKeys`
4. ✅ Utworzyć `ResponseDataKeys`
5. ✅ Utworzyć `ConfigKeys` w `preprocessor/utils/constants.py`

### Faza 2: WYSOKIE (Week 2)
6. ✅ Utworzyć `EmbeddingKeys`
7. ✅ Utworzyć `FrameProcessingKeys`
8. ✅ Utworzyć `HttpResponseKeys`
9. ✅ Utworzyć `ElasticsearchIndexNames`

### Faza 3: ŚREDNIE (Week 3)
10. ✅ Utworzyć klasy z Kategorii B (wybrane)
11. ✅ Zrefaktoryzować kod używający tych kluczy

### Faza 4: WERYFIKACJA (Week 4)
12. ✅ Uruchomić testy
13. ✅ Zweryfikować czy wszystkie zmiany działają
14. ✅ Usunąć stare raw stringi

---

## UWAGI SPECJALNE

### 1. Konflikt nazw
Niektóre klucze jak `"type"`, `"name"`, `"text"` występują w wielu kontekstach:
- Elasticsearch mapping: `"type"`
- Response data: `"type"`
- Character: `"name"`
- Series: `"name"`

**Rozwiązanie:** Rozdzielić na osobne klasy według kontekstu.

### 2. Już istniejące klasy
Sprawdzić czy te klasy już istnieją w `constants.py`:
- `DatabaseKeys` ✅
- `SegmentKeys` ✅
- `EpisodeMetadataKeys` ✅
- `JwtPayloadKeys` ✅
- `AuthKeys` ✅
- `HttpHeaderKeys` ✅

**Rozwiązanie:** Rozszerzyć istniejące klasy zamiast tworzyć nowe.

### 3. Click context_settings
String `"show_default"` występuje 18 razy w Click commands:
```python
@click.command(context_settings={"show_default": True})
```

**Rozwiązanie:**
```python
class ClickContextKeys:
    SHOW_DEFAULT = "show_default"

CLICK_DEFAULT_CONTEXT = {"show_default": True}
```

### 4. File extensions/suffixes
Stringi jak `"json"`, `"segmented"` są już częściowo w `FILE_SUFFIXES` i `FILE_EXTENSIONS`.

**Rozwiązanie:** Zweryfikować kompletność tych słowników.

---

## PRZYKŁADY REFAKTORYZACJI

### Przed:
```python
# bot/search/elastic_search_manager.py
result = await es.search(
    index="ranczo_segments",
    body={
        "query": {
            "bool": {
                "must": [
                    {"term": {"episode_metadata.season": season}}
                ]
            }
        }
    }
)
hits = result["hits"]["hits"]
for hit in hits:
    source = hit["_source"]
    text = source.get("text")
```

### Po:
```python
from bot.utils.constants import ElasticsearchKeys as ESK, ElasticsearchIndexNames as ESIN

result = await es.search(
    index=ESIN.SEGMENTS,
    body={
        ESK.QUERY: {
            ESK.BOOL: {
                ESK.MUST: [
                    {ESK.TERM: {f"{ESK.EPISODE_METADATA}.{ESK.SEASON}": season}}
                ]
            }
        }
    }
)
hits = result[ESK.HITS][ESK.HITS]
for hit in hits:
    source = hit[ESK.SOURCE]
    text = source.get(ESK.TEXT)
```

---

## METRYKI SUKCESU

### Przed refaktoryzacją:
- Raw stringi (3+ wystąpienia): **226**
- Raw stringi (2 wystąpienia): **94**
- Razem do refaktoryzacji: **320**

### Cel po refaktoryzacji:
- Raw stringi (3+ wystąpienia): **0**
- Raw stringi (2 wystąpienia): **0**
- Pokrycie stałymi: **100%** dla kategorii A i B

---

## KOŃCOWE ZALECENIA

1. **Priorytet 1 (MUST):** Wszystkie klucze z kategorii A (226 stringów, 3+ wystąpienia)
2. **Priorytet 2 (SHOULD):** Wybrane klucze z kategorii B związane z API i konfiguracją
3. **Priorytet 3 (COULD):** Kategoria C - tylko krytyczne dla bezpieczeństwa

**Szacowany czas:** 4 tygodnie pracy (przy założeniu refaktoryzacji ~80 stringów/tydzień)

**Ryzyko:** Niskie - kod jest dobrze otestowany, zmiany są mechaniczne

**Korzyści:**
- Eliminacja magic strings
- Lepsza wykrywalność błędów w czasie kompilacji
- Łatwiejsze refaktoryzowanie w przyszłości
- Zgodność z instrukcjami projektu (styl kod maksymalnie hermetyczny)

---

**Autor raportu:** Claude Code Agent
**Narzędzie analizy:** `analyze_raw_strings.py`
**Pełny raport:** `/tmp/raw_strings_report.txt`

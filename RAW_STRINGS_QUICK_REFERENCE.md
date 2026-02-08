# QUICK REFERENCE - TOP 50 RAW STRINGÓW DO REFAKTORYZACJI

## PODSUMOWANIE STATYSTYK

- **Całkowita liczba unikalnych stringów:** 600
- **Wysokie ryzyko (3+ wystąpienia):** 226 stringów
- **Średnie ryzyko (2 wystąpienia):** 94 stringi
- **Niskie ryzyko (1 wystąpienie):** 280 stringów

---

## TOP 50 STRINGÓW (3+ WYSTĄPIENIA)

| # | String | Wystąpienia | Sugerowana klasa |
|---|--------|-------------|------------------|
| 1 | `"type"` | 177 | **ElasticsearchKeys** |
| 2 | `"text"` | 83 | **SegmentDataKeys** |
| 3 | `"episode_info"` | 60 | **EpisodeDataKeys** |
| 4 | `"series_name"` | 53 | **ConfigKeys** |
| 5 | `"episodes_info_json"` | 49 | **ConfigKeys** |
| 6 | `"segments"` | 44 | **SegmentDataKeys** |
| 7 | `"start"` | 41 | **SegmentDataKeys** |
| 8 | `"end"` | 41 | **SegmentDataKeys** |
| 9 | `"words"` | 33 | **SegmentDataKeys** |
| 10 | `"season"` | 31 | **EpisodeDataKeys** |
| 11 | `"name"` | 31 | ⚠️ **Multiple** (context-dependent) |
| 12 | `"term"` | 31 | **ElasticsearchKeys** |
| 13 | `"properties"` | 30 | **ElasticsearchKeys** |
| 14 | `"episode_number"` | 30 | **EpisodeDataKeys** |
| 15 | `"video_path"` | 27 | **EpisodeDataKeys** |
| 16 | `"output_dir"` | 26 | **ConfigKeys** |
| 17 | `"episode_id"` | 25 | **EpisodeDataKeys** |
| 18 | `"title"` | 23 | **EpisodeDataKeys** |
| 19 | `"state_manager"` | 22 | **ConfigKeys** |
| 20 | `"hits"` | 18 | **ElasticsearchKeys** |
| 21 | `"show_default"` | 18 | **ClickContextKeys** |
| 22 | `"videos"` | 17 | **ConfigKeys** |
| 23 | `"transcription_jsons"` | 17 | **ConfigKeys** |
| 24 | `"episode_metadata"` | 16 | **EpisodeDataKeys** |
| 25 | `"premiere_date"` | 16 | **EpisodeDataKeys** |
| 26 | `"device"` | 15 | **ConfigKeys** |
| 27 | `"frames"` | 15 | **FrameProcessingKeys** |
| 28 | `"start_time"` | 14 | **SegmentDataKeys** |
| 29 | `"viewership"` | 14 | **EpisodeDataKeys** |
| 30 | `"embedding"` | 14 | **EmbeddingKeys** |
| 31 | `"end_time"` | 12 | **SegmentDataKeys** |
| 32 | `"segment_range"` | 12 | **SegmentDataKeys** |
| 33 | `"json"` | 12 | **FilePatternKeys** |
| 34 | `"speaker"` | 12 | **SegmentDataKeys** |
| 35 | `"nested"` | 12 | **ElasticsearchKeys** |
| 36 | `"path"` | 12 | ⚠️ **Multiple** (context-dependent) |
| 37 | `"id"` | 11 | **SegmentDataKeys** lub **ElasticsearchKeys** |
| 38 | `"query"` | 11 | **ElasticsearchKeys** lub **ResponseDataKeys** |
| 39 | `"confidence"` | 11 | **FrameProcessingKeys** |
| 40 | `"characters"` | 11 | **FrameProcessingKeys** lub **CharacterReferenceKeys** |
| 41 | `"language"` | 11 | **TranscriptionKeys** lub **ConfigKeys** |
| 42 | `"scene_timestamps_dir"` | 11 | **ConfigKeys** |
| 43 | `"frame_number"` | 11 | **FrameProcessingKeys** |
| 44 | `"format"` | 11 | **ConfigKeys** |
| 45 | `"detections"` | 11 | **FrameProcessingKeys** |
| 46 | `"timestamp"` | 10 | **SegmentDataKeys** |
| 47 | `"frames_dir"` | 10 | **ConfigKeys** |
| 48 | `"batch_size"` | 10 | **ConfigKeys** |
| 49 | `"count"` | 10 | **ElasticsearchKeys** |
| 50 | `"language_code"` | 10 | **ConfigKeys** lub **TranscriptionKeys** |

---

## GRUPY STRINGÓW WEDŁUG KLAS

### 🔴 ElasticsearchKeys (HIGHEST PRIORITY)
**Wystąpienia:** ~250 (najwięcej!)

Główne klucze:
- `"type"` (177) - mapping type
- `"term"` (31) - query term
- `"properties"` (30) - mapping properties
- `"hits"` (18) - response hits
- `"nested"` (12) - nested query
- `"query"` (11) - query object
- `"count"` (10) - count operation

**Pliki do refaktoryzacji:**
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/bot/search/elastic_search_manager.py` (60+ stringów)
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/search/elastic_manager.py` (150+ stringów)
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/cli/commands/search.py` (80+ stringów)

---

### 🟠 SegmentDataKeys (HIGH PRIORITY)
**Wystąpienia:** ~180

Główne klucze:
- `"text"` (83)
- `"segments"` (44)
- `"start"` (41)
- `"end"` (41)
- `"words"` (33)
- `"start_time"` (14)
- `"end_time"` (12)
- `"segment_range"` (12)
- `"speaker"` (12)
- `"timestamp"` (10)

**Pliki do refaktoryzacji:**
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/bot/search/elastic_search_manager.py`
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/embeddings/embedding_generator.py`
- `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/indexing/elastic_document_generator.py`

---

### 🟡 EpisodeDataKeys (HIGH PRIORITY)
**Wystąpienia:** ~160

Główne klucze:
- `"episode_info"` (60)
- `"season"` (31)
- `"episode_number"` (30)
- `"video_path"` (27)
- `"episode_id"` (25)
- `"title"` (23)
- `"episode_metadata"` (16)
- `"premiere_date"` (16)
- `"viewership"` (14)

**Pliki do refaktoryzacji:**
- Praktycznie wszystkie procesory w `preprocessor/`
- Wszystkie handlery w `bot/handlers/`

---

### 🟢 ConfigKeys (MEDIUM-HIGH PRIORITY)
**Wystąpienia:** ~140

Główne klucze:
- `"series_name"` (53)
- `"episodes_info_json"` (49)
- `"output_dir"` (26)
- `"state_manager"` (22)
- `"videos"` (17)
- `"transcription_jsons"` (17)
- `"device"` (15)
- `"scene_timestamps_dir"` (11)
- `"frames_dir"` (10)
- `"batch_size"` (10)
- `"language_code"` (10)

**Pliki do refaktoryzacji:**
- Wszystkie pliki w `preprocessor/cli/commands/`
- `preprocessor/cli/pipeline/steps.py`
- `preprocessor/core/base_processor.py`

---

### 🔵 FrameProcessingKeys (MEDIUM PRIORITY)
**Wystąpienia:** ~60

Główne klucze:
- `"frames"` (15)
- `"confidence"` (11)
- `"characters"` (11)
- `"frame_number"` (11)
- `"detections"` (11)

**Pliki do refaktoryzacji:**
- `preprocessor/video/frame_subprocessors.py`
- `preprocessor/video/frame_exporter.py`
- `preprocessor/characters/detector.py`

---

### 🟣 EmbeddingKeys (MEDIUM PRIORITY)
**Wystąpienia:** ~40

Główne klucze:
- `"embedding"` (14)
- `"text_embedding"` (~10)
- `"video_embedding"` (~10)
- `"embedding_dimension"` (~10)

**Pliki do refaktoryzacji:**
- `preprocessor/embeddings/embedding_generator.py`
- `preprocessor/indexing/elastic_document_generator.py`

---

## KONFLIKTOWE STRINGI (MULTIPLE CONTEXTS)

### ⚠️ `"name"` (31 wystąpień)
**Konteksty:**
1. Character name → `CharacterReferenceKeys.NAME`
2. Series name → `ConfigKeys.NAME` (alias for SERIES_NAME)
3. Episode name → możliwe inne użycia

**Rozwiązanie:** Używać specyficznej klasy w zależności od kontekstu.

### ⚠️ `"path"` (12 wystąpień)
**Konteksty:**
1. Elasticsearch nested path → `ElasticsearchKeys.PATH`
2. File path → różne klasy (video_path, frame_path, etc.)

**Rozwiązanie:** Oddzielne stałe dla każdego kontekstu.

### ⚠️ `"id"` (11 wystąpień)
**Konteksty:**
1. Segment ID → `SegmentKeys.ID`
2. Episode ID → `EpisodeDataKeys.EPISODE_ID`
3. Elasticsearch _id → `ElasticsearchKeys.ID`

**Rozwiązanie:** Używać pełnej nazwy (EPISODE_ID, SEGMENT_ID, etc.)

---

## PLIKI Z NAJWIEKSZĄ LICZBĄ RAW STRINGÓW

### Top 10 plików do refaktoryzacji:

| Plik | Est. raw strings | Priorytet |
|------|------------------|-----------|
| `preprocessor/search/elastic_manager.py` | ~150 | 🔴 CRITICAL |
| `preprocessor/cli/commands/search.py` | ~80 | 🔴 CRITICAL |
| `bot/search/elastic_search_manager.py` | ~60 | 🔴 CRITICAL |
| `preprocessor/indexing/elastic_document_generator.py` | ~50 | 🟠 HIGH |
| `preprocessor/embeddings/embedding_generator.py` | ~40 | 🟠 HIGH |
| `preprocessor/cli/pipeline/steps.py` | ~35 | 🟡 MEDIUM-HIGH |
| `preprocessor/video/frame_subprocessors.py` | ~30 | 🟡 MEDIUM-HIGH |
| `bot/platforms/rest_runner.py` | ~25 | 🟡 MEDIUM-HIGH |
| `preprocessor/core/base_processor.py` | ~20 | 🟢 MEDIUM |
| `bot/handlers/not_sending_videos/*.py` | ~18 avg | 🟢 MEDIUM |

---

## SZYBKI START - CO ZROBIĆ?

### 1. Utworzyć klasy stałych (2h)
```bash
# Edytować pliki:
bot/utils/constants.py
preprocessor/utils/constants.py
```

Dodać klasy:
- ElasticsearchKeys
- ElasticsearchIndexNames
- SegmentDataKeys
- EpisodeDataKeys
- ConfigKeys
- ResponseDataKeys
- EmbeddingKeys
- FrameProcessingKeys
- i inne z listy

### 2. Refaktoryzacja TOP 3 plików (8h)
```bash
# Refaktoryzować w kolejności:
1. preprocessor/search/elastic_manager.py
2. preprocessor/cli/commands/search.py
3. bot/search/elastic_search_manager.py
```

### 3. Testy i weryfikacja (2h)
```bash
pytest bot/tests/ -v
ruff check bot/ preprocessor/
mypy bot/ preprocessor/
```

---

## SZACUNKI CZASOWE

| Zakres | Pliki | Stringi | Czas |
|--------|-------|---------|------|
| **Faza 1: Krityczne** | ~10 | ~250 | 12h |
| **Faza 2: Wysokie** | ~15 | ~150 | 16h |
| **Faza 3: Średnie** | ~20 | ~70 | 10h |
| **RAZEM** | **~45** | **~470** | **38h** |

---

## NARZĘDZIA POMOCNICZE

### Sprawdzenie postępu:
```bash
# Uruchom skrypt analizy
python3 analyze_raw_strings.py

# Sprawdź konkretny plik
grep -o '\.get\s*(\s*["'\'']\w\+["'\'']' <file>.py | wc -l

# Znajdź wszystkie .get() w pliku
grep -n '\.get(' <file>.py
```

### Automatyczna refaktoryzacja (opcjonalnie):
```bash
# Find & replace w edytorze (VS Code, PyCharm)
# Regex search: \.get\("(\w+)"\)
# Replace with: .get(KEYS.$1)
```

---

## DOKUMENTY POWIĄZANE

1. **RAW_STRINGS_ANALYSIS_FINAL.md** - Pełna analiza z kategoriami i priorytetami
2. **RAW_STRINGS_IMPLEMENTATION_GUIDE.md** - Przewodnik implementacji z przykładami
3. **analyze_raw_strings.py** - Skrypt analizy (uruchom ponownie po refaktoryzacji)

---

**Utworzono:** 2026-02-08
**Narzędzie:** Claude Code Agent + analyze_raw_strings.py
**Status:** ✅ Gotowe do użycia

# PLAN IMPLEMENTACJI: Multi-Series Support dla Preprocessora

> **Status:** PLAN - NIE WDROŻONE
>
> **Data:** 2026-02-08
>
> **Cel:** Umożliwić preprocessing wielu seriali w tym samym środowisku, gdzie każdy serial ma swój dedykowany folder na input i output

---

## 1. PROBLEM DO ROZWIĄZANIA

### 1.1 Obecna sytuacja

**INPUT:**
```
/input_data/
  ├── S01/
  ├── S02/
  └── S03/
```

**OUTPUT:**
```
/app/output_data/
  ├── transcoded_videos/
  ├── transcriptions/
  ├── scene_timestamps/
  ├── exported_frames/
  └── ranczo_episodes.json
```

**Problemy:**
- Można przetwarzać tylko jeden serial naraz
- Mieszanie plików różnych seriali w tym samym katalogu
- Brak izolacji danych między serialami
- Trudność w zarządzaniu wieloma serialami

### 1.2 Docelowa sytuacja

**INPUT:**
```
/input_data/
  ├── ranczo/
  │   ├── S01/
  │   ├── S02/
  │   └── S03/
  └── kiepscy/
      ├── S01/
      └── S02/
```

**OUTPUT:**
```
/app/output_data/
  ├── ranczo/
  │   ├── transcoded_videos/
  │   ├── transcriptions/
  │   ├── scene_timestamps/
  │   ├── exported_frames/
  │   ├── ranczo_episodes.json
  │   └── ranczo_characters.json
  └── kiepscy/
      ├── transcoded_videos/
      ├── transcriptions/
      ├── kiepscy_episodes.json
      └── kiepscy_characters.json
```

**Korzyści:**
- ✅ Pełna izolacja danych między serialami
- ✅ Możliwość przetwarzania wielu seriali równolegle
- ✅ Przejrzysta struktura katalogów
- ✅ Łatwe zarządzanie i czyszczenie danych per serial

---

## 2. KLUCZOWA ZMIANA ARCHITEKTONICZNA

### 2.1 Dynamiczne ścieżki bazowe

**PRZED:**
```python
# preprocessor/config/config.py:24
BASE_OUTPUT_DIR = Path("/app/output_data")
```

**PO:**
```python
# preprocessor/config/config.py:24
def get_base_output_dir(series_name: Optional[str] = None) -> Path:
    base = Path("/app/output_data") if is_docker else Path("preprocessor/output_data")
    if series_name:
        return base / series_name.lower()
    return base

def get_output_path(relative_path: str, series_name: Optional[str] = None) -> Path:
    return get_base_output_dir(series_name) / relative_path
```

### 2.2 Input path validation

**Dodaj w `base_processor._create_video_processing_items()`:**
```python
def _create_video_processing_items(
    self,
    source_path: Path,
    extensions: List[str],
    episode_manager: "EpisodeManager",
    skip_unparseable: bool = True,
    subdirectory_filter: Optional[str] = None,
) -> List[ProcessingItem]:
    series_name = episode_manager.series_name

    # Sprawdź czy source_path wskazuje na /input_data/{series_name}/
    if source_path.name != series_name:
        # User podał /input_data/ -> dodaj series_name
        source_path = source_path / series_name

    if not source_path.exists():
        raise FileNotFoundError(
            f"Input directory does not exist: {source_path}\n"
            f"Expected structure: /input_data/{series_name}/S01/, /input_data/{series_name}/S02/, etc.\n\n"
            f"Migration guide:\n"
            f"  mkdir -p /input_data/{series_name}\n"
            f"  mv /input_data/S* /input_data/{series_name}/"
        )

    # ... reszta logiki
```

---

## 3. PLIKI DO MODYFIKACJI

### 3.1 CORE CONFIG (Priorytet: KRYTYCZNY ⚠️)

#### `preprocessor/config/config.py`

**Lokalizacja:** `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/config/config.py`

**Zmiany:**
1. **Linia 24:** Zastąp `BASE_OUTPUT_DIR` funkcją `get_base_output_dir(series_name)`
2. **Linia 27:** Zmień `get_output_path()` aby przyjmowała `series_name`
3. **Linie 92-273:** Wszystkie dataclass settings - zmień z static paths na dynamic

**Dotknięte sekcje:**
- `TranscodeConfig` (linia 92)
- `TranscriptionConfig` (linia 134)
- `EmbeddingConfig` (linia 168)
- `ElasticsearchConfig` (linia 193)
- `FrameExportConfig` (linia 213)
- `CharacterConfig` (linia 228)
- `SceneDetectionConfig` (linia 254)
- `ValidationConfig` (linia 264)

**Przykład zmiany:**
```python
# BYŁO:
@dataclass
class TranscodeConfig:
    output_dir: Path = BASE_OUTPUT_DIR / "transcoded_videos"
    # ...

# MA BYĆ:
@dataclass
class TranscodeConfig:
    # output_dir będzie przekazywane dynamicznie w runtime
    # lub użyj factory function
    @staticmethod
    def get_output_dir(series_name: str) -> Path:
        return get_base_output_dir(series_name) / "transcoded_videos"
```

#### `preprocessor/core/output_path_builder.py`

**Lokalizacja:** `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/core/output_path_builder.py`

**Zmiany - WSZYSTKIE metody muszą przyjąć parametr `series_name`:**

| Linia | Metoda | Zmiana |
|-------|--------|--------|
| 15 | `get_episode_dir()` | Dodaj `series_name: str` param |
| 20 | `get_season_dir()` | Bez zmian (tylko season code) |
| 25 | `build_transcription_path()` | Dodaj `series_name: str` param |
| 33 | `build_output_path()` | Dodaj `series_name: str` param |
| 39 | `build_video_path()` | Dodaj `series_name: str` param |
| 47 | `build_elastic_video_path()` | Już ma `series_name` - OK |
| 54 | `build_embedding_path()` | Dodaj `series_name: str` param |
| 62 | `build_scene_path()` | Dodaj `series_name: str` param |
| 70 | `build_elastic_document_path()` | Dodaj `series_name: str` param |

**Przykład zmiany:**
```python
# BYŁO (linia 15):
@staticmethod
def get_episode_dir(episode_info, base_subdir: str) -> Path:
    season_code = f"S{episode_info.season:02d}"
    episode_code = f"E{episode_info.relative_episode:02d}"
    return BASE_OUTPUT_DIR / base_subdir / season_code / episode_code

# MA BYĆ:
@staticmethod
def get_episode_dir(episode_info, base_subdir: str, series_name: str) -> Path:
    season_code = f"S{episode_info.season:02d}"
    episode_code = f"E{episode_info.relative_episode:02d}"
    from preprocessor.config.config import get_base_output_dir
    return get_base_output_dir(series_name) / base_subdir / season_code / episode_code
```

#### `preprocessor/core/base_processor.py`

**Lokalizacja:** `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/core/base_processor.py`

**Zmiany:**
1. **Linia 277:** `_create_video_processing_items()` - dodaj input path validation (kod powyżej)
2. **Linia 292-297:** Zmień glob pattern aby uwzględniał `series_name`

---

### 3.2 VIDEO PROCESSORS (Priorytet: WYSOKI 🔴)

#### `preprocessor/video/transcoder.py`
**Zmiana:** Linia 72 - `OutputPathBuilder.build_video_path()` dodaj `series_name`

#### `preprocessor/video/frame_exporter.py`
**Zmiana:** Wszystkie wywołania `OutputPathBuilder.*` z `series_name`

#### `preprocessor/video/scene_detector.py`
**Zmiana:** Wszystkie wywołania `OutputPathBuilder.*` z `series_name`

#### `preprocessor/video/base_video_processor.py`
**Zmiana:** Linia 33 - `self.input_videos` będzie wskazywać na `/input_data/{series_name}/`

---

### 3.3 TRANSCRIPTION PROCESSORS (Priorytet: WYSOKI 🔴)

#### `preprocessor/transcription/generator.py`
**Zmiana:** Wszystkie wywołania `OutputPathBuilder.*` z `series_name`

#### `preprocessor/transcription/elevenlabs.py`
**Zmiana:** Wszystkie wywołania `OutputPathBuilder.*` z `series_name`

#### `preprocessor/transcription/processors/sound_separator.py`
**Zmiana:** Output paths z `series_name`

---

### 3.4 EMBEDDINGS & INDEXING (Priorytet: WYSOKI 🔴)

#### `preprocessor/embeddings/embedding_generator.py`
**Zmiana:** Output paths z `series_name`

#### `preprocessor/indexing/elastic_document_generator.py`
**Zmiany:**
- Linia 60: `output_dir` hardcoded - zmień na `get_base_output_dir(series_name) / "elastic_documents"`
- Wszystkie wywołania `OutputPathBuilder.*` z `series_name`

#### `preprocessor/indexing/archive_generator.py`
**Zmiana:** Output archives per series: `get_base_output_dir(series_name) / "archives"`

#### `preprocessor/indexing/elasticsearch.py`
**Zmiana (opcjonalna):** Index naming per series lub shared index z `series_name` field

---

### 3.5 CLI COMMANDS (Priorytet: ŚREDNI 🟡)

#### `preprocessor/cli/commands/run_all.py`

**Zmiany:**
1. **Linia 187:**
   ```python
   # BYŁO:
   default_episodes_json = Path("/app/output_data") / f"{series_name}_episodes.json"

   # MA BYĆ:
   from preprocessor.config.config import get_base_output_dir
   default_episodes_json = get_base_output_dir(series_name) / f"{series_name}_episodes.json"
   ```

2. **Linia 200:**
   ```python
   # BYŁO:
   default_characters_json = Path("/app/output_data") / f"{series_name}_characters.json"

   # MA BYĆ:
   default_characters_json = get_base_output_dir(series_name) / f"{series_name}_characters.json"
   ```

3. **Linia 255:**
   ```python
   # BYŁO:
   metadata_output_dir = Path("/app/output_data/processing_metadata")

   # MA BYĆ:
   metadata_output_dir = get_base_output_dir(series_name) / "processing_metadata"
   ```

#### `preprocessor/cli/commands/transcode.py`
**Zmiana:** Linia 21 - default `--transcoded-videos` z `series_name`

#### Pozostałe komendy
- `transcribe.py`
- `index.py`
- `generate_archives.py`
- `embed.py`
- `scrape_episodes.py`

**Zmiana:** Default paths z `get_base_output_dir(series_name)`

---

### 3.6 PIPELINE STEPS (Priorytet: ŚREDNI 🟡)

#### `preprocessor/cli/pipeline/steps.py`

**Zmiany - wszystkie funkcje `run_*_step()`:**

| Linia | Funkcja | Zmiana |
|-------|---------|--------|
| 15 | `run_scrape_step()` | Output path z `series_name` |
| 35 | `run_character_scrape_step()` | Output path z `series_name` |
| 95 | `run_character_reference_download_step()` | `output_dir` z `get_base_output_dir(name)` |
| 115 | `run_character_reference_processing_step()` | Output paths z `series_name` |
| 152 | `run_transcode_step()` | Przekaż `series_name` do VideoTranscoder |
| 185 | `run_transcribe_step()` | Przekaż `series_name` do processorów |
| 235 | `run_sound_separation_step()` | Output paths z `series_name` |
| 263 | `run_text_analysis_step()` | Output paths z `series_name` |
| 281 | `run_scene_step()` | Przekaż `series_name` do SceneDetector |
| 305 | `run_frame_export_step()` | Przekaż `series_name` do FrameExporter |
| 328 | `run_embedding_step()` | Output paths z `series_name` |
| 351 | `run_frame_processing_step()` | Output paths z `series_name` |
| 408 | `run_elastic_documents_step()` | Przekaż `series_name` do ElasticDocumentGenerator |
| 425 | `run_archive_generation_step()` | Output paths z `series_name` |
| 438 | `run_index_step()` | Index naming z `series_name` (opcjonalnie) |
| 452 | `run_validation_step()` | Validation paths z `series_name` |

---

### 3.7 CHARACTER DETECTION (Priorytet: ŚREDNI 🟡)

#### `preprocessor/characters/detector.py`
**Zmiana:** Output paths z `series_name`

#### `preprocessor/characters/reference_downloader.py`
**Zmiana:** Output paths z `series_name`

#### `preprocessor/characters/reference_processor.py`
**Zmiana:** Output paths z `series_name`

---

### 3.8 SCRAPERS (Priorytet: ŚREDNI 🟡)

#### `preprocessor/scraping/episode_scraper.py`

**Zmiany:**
1. **Linia 21:** `videos_dir` validation - uwzględnij `/input_data/{series_name}/`
2. **Linia 80-84:** `__count_video_files()` - skanowanie z `series_name` w ścieżce

---

### 3.9 VALIDATION & UTILITIES (Priorytet: NISKI 🟢)

#### `preprocessor/validation/validator.py`
**Zmiana:** Output paths z `series_name`

#### `preprocessor/text_analysis/text_analyzer.py`
**Zmiana:** Output paths z `series_name`

---

### 3.10 DOCKER & DEPLOYMENT (Priorytet: INFORMACYJNY ℹ️)

#### `preprocessor/docker-compose.yml`

**BRAK ZMIAN - volumes mapują całe katalogi:**
```yaml
volumes:
  - ./input_data:/input_data:ro  # Mapuje /input_data z wszystkimi subdirectories
  - ./output_data:/app/output_data  # Mapuje /output_data z wszystkimi subdirectories
```

Struktura wewnątrz tych katalogów jest zarządzana przez aplikację, nie przez Docker.

---

## 4. BACKWARD COMPATIBILITY

### 4.1 Strategia: Strict Mode (zalecana)

**Podejście:**
- Wymaga, aby wszystkie pliki były w `/input_data/{series_name}/`
- Jeśli struktura jest niepoprawna → **jasny error message z instrukcją migracji**
- Proste, przewidywalne, bezpieczne

**Error message:**
```
FileNotFoundError: Input directory structure incorrect!

Expected: /input_data/kiepscy/S01/, /input_data/kiepscy/S02/, ...
Got: /input_data/

Migration guide:
  mkdir -p /input_data/kiepscy
  mv /input_data/S* /input_data/kiepscy/
```

### 4.2 Alternatywa: Auto-migration (NIE zalecana)

**Podejście:**
- Jeśli wykryto `/input_data/S01/` bez `series_name` → użyj `series_name` z CLI
- Automatycznie przenieś pliki lub stwórz symlinki

**Problemy:**
- Ryzyko utraty danych
- Niejasne zachowanie
- Trudne w debugowaniu
- Może zepsuć istniejące setupy

**REKOMENDACJA:** NIE implementować auto-migration.

---

## 5. PLAN IMPLEMENTACJI KROK PO KROKU

### Faza 1: Core Infrastructure (1-2 dni)
- [ ] Zmodyfikuj `preprocessor/config/config.py`
  - [ ] Dodaj funkcję `get_base_output_dir(series_name)`
  - [ ] Dodaj funkcję `get_output_path(relative_path, series_name)`
  - [ ] Zaktualizuj wszystkie dataclass configs
- [ ] Zmodyfikuj `preprocessor/core/output_path_builder.py`
  - [ ] Dodaj parametr `series_name` do wszystkich metod (10 metod)
  - [ ] Zmień `BASE_OUTPUT_DIR` na `get_base_output_dir(series_name)`
- [ ] Zmodyfikuj `preprocessor/core/base_processor.py`
  - [ ] Dodaj input path validation w `_create_video_processing_items()`
  - [ ] Dodaj automatyczne dodawanie `series_name` do source_path
- [ ] **Testy unit:** Sprawdź czy funkcje zwracają poprawne ścieżki

### Faza 2: Video & Transcription Processors (2-3 dni)
- [ ] Zaktualizuj `preprocessor/video/transcoder.py`
- [ ] Zaktualizuj `preprocessor/video/frame_exporter.py`
- [ ] Zaktualizuj `preprocessor/video/scene_detector.py`
- [ ] Zaktualizuj `preprocessor/transcription/generator.py`
- [ ] Zaktualizuj `preprocessor/transcription/elevenlabs.py`
- [ ] Zaktualizuj `preprocessor/transcription/processors/sound_separator.py`
- [ ] **Testy integracyjne:** Transcode + transcribe jednego odcinka

### Faza 3: Embeddings & Indexing (1-2 dni)
- [ ] Zaktualizuj `preprocessor/embeddings/embedding_generator.py`
- [ ] Zaktualizuj `preprocessor/indexing/elastic_document_generator.py`
- [ ] Zaktualizuj `preprocessor/indexing/archive_generator.py`
- [ ] Zaktualizuj `preprocessor/indexing/elasticsearch.py` (index naming)
- [ ] **Testy:** Full pipeline do indexing

### Faza 4: CLI & Pipeline (1 dzień)
- [ ] Zaktualizuj `preprocessor/cli/commands/run_all.py`
- [ ] Zaktualizuj `preprocessor/cli/commands/transcode.py`
- [ ] Zaktualizuj pozostałe komendy CLI (7 plików)
- [ ] Zaktualizuj `preprocessor/cli/pipeline/steps.py` (13 funkcji)
- [ ] **Testy CLI:** Pełny pipeline przez `run-all`

### Faza 5: Characters, Scrapers, Utilities (1 dzień)
- [ ] Zaktualizuj `preprocessor/characters/*` (3 pliki)
- [ ] Zaktualizuj `preprocessor/scraping/*` (2 pliki)
- [ ] Zaktualizuj `preprocessor/validation/*`
- [ ] Zaktualizuj `preprocessor/text_analysis/*`
- [ ] **Code review:** Grep po hardcoded paths

### Faza 6: Documentation & Testing (1 dzień)
- [ ] Zaktualizuj `preprocessor/README.md`
  - [ ] Nowe przykłady z multi-series
  - [ ] Migration guide ze starej struktury
  - [ ] Troubleshooting section
- [ ] Zaktualizuj `.claude/app_logic_notes.md`
- [ ] **Test akceptacyjny 1:** Nowa seria od zera
- [ ] **Test akceptacyjny 2:** Dwie serie jednocześnie
- [ ] **Test akceptacyjny 3:** Migration error message

---

## 6. TESTY AKCEPTACYJNE

### Test 1: Nowa seria od zera

```bash
# Setup
mkdir -p preprocessor/input_data/kiepscy/S01
cp sample_videos/*.mp4 preprocessor/input_data/kiepscy/S01/

# Rename files (już zrobione wcześniej)
# Pliki muszą być w formacie S01E001.Title.mp4

# Run preprocessing
./run-preprocessor.sh run-all /input_data/kiepscy \
  --series-name kiepscy \
  --scrape-urls https://pl.wikipedia.org/wiki/Lista_odcinków_serialu_Świat_według_Kiepskich \
  --character-urls https://pl.wikipedia.org/wiki/Lista_postaci_serialu_Świat_według_Kiepskich \
  --parser-mode premium \
  --search-mode premium

# Weryfikacja
ls preprocessor/output_data/kiepscy/transcoded_videos/S01/
ls preprocessor/output_data/kiepscy/transcriptions/S01/
ls preprocessor/output_data/kiepscy/elastic_documents/
ls preprocessor/output_data/kiepscy/archives/
cat preprocessor/output_data/kiepscy/kiepscy_episodes.json
cat preprocessor/output_data/kiepscy/kiepscy_characters.json

# Oczekiwany rezultat: Wszystkie pliki w /output_data/kiepscy/
```

### Test 2: Dwie serie jednocześnie

```bash
# Setup serie 1: Ranczo
mkdir -p preprocessor/input_data/ranczo/S01
cp ranczo_videos/*.mp4 preprocessor/input_data/ranczo/S01/

# Setup serie 2: Kiepscy (już istnieje z Test 1)

# Run preprocessing dla Ranczo
./run-preprocessor.sh run-all /input_data/ranczo \
  --series-name ranczo \
  --scrape-urls https://pl.wikipedia.org/wiki/Ranczo_(serial_telewizyjny) \
  --skip-character-processing

# Weryfikacja izolacji
ls preprocessor/output_data/ranczo/
ls preprocessor/output_data/kiepscy/

# Sprawdź że:
# 1. Foldery są całkowicie osobne
# 2. Pliki Ranczo nie mieszają się z Kiepscy
# 3. Elasticsearch ma osobne dokumenty (lub proper series_name field)

# Oczekiwany rezultat: Pełna izolacja danych
```

### Test 3: Migration ze starej struktury (Error Message)

```bash
# Setup: Symuluj starą strukturę
mkdir -p preprocessor/input_data/S01
cp old_videos/*.mp4 preprocessor/input_data/S01/

# Próba uruchomienia
./run-preprocessor.sh run-all /input_data \
  --series-name ranczo

# Oczekiwany rezultat: ERROR
# FileNotFoundError: Input directory structure incorrect!
# Expected: /input_data/ranczo/S01/, /input_data/ranczo/S02/, ...
# Got: /input_data/
#
# Migration guide:
#   mkdir -p /input_data/ranczo
#   mv /input_data/S* /input_data/ranczo/

# Wykonaj migrację
mkdir -p preprocessor/input_data/ranczo
mv preprocessor/input_data/S* preprocessor/input_data/ranczo/

# Ponowna próba
./run-preprocessor.sh run-all /input_data/ranczo --series-name ranczo

# Oczekiwany rezultat: SUCCESS
```

---

## 7. POTENCJALNE PROBLEMY I ROZWIĄZANIA

### Problem 1: Hardcoded paths w wielu miejscach
**Symptom:** Niektóre pliki nadal trafiają do `/app/output_data/` zamiast `/app/output_data/{series_name}/`

**Rozwiązanie:**
```bash
# Grep po całym repozytorium
cd preprocessor
grep -r '"/app/output_data"' --include="*.py" | grep -v "def get_base_output_dir"
grep -r '"output_data/"' --include="*.py" | grep -v "def get_base_output_dir"
grep -r 'Path("output_data")' --include="*.py"

# Zamień wszystkie wystąpienia na get_base_output_dir(series_name)
```

### Problem 2: State manager resume nie działa po zmianie struktury
**Symptom:** `--no-state` flag nie pomaga, resume szuka plików w złych lokalizacjach

**Rozwiązanie:**
- State file nazwany `{series_name}_state.json` zamiast globalnego `state.json`
- Lokalizacja: `/app/output_data/{series_name}/processing_metadata/state.json`

**Kod:**
```python
# preprocessor/cli/utils.py lub podobny
def create_state_manager(series_name: str, no_state: bool):
    if no_state:
        return None
    state_file = get_base_output_dir(series_name) / "processing_metadata" / "state.json"
    return StateManager(state_file)
```

### Problem 3: Elasticsearch index naming conflicts
**Symptom:** Dwie serie używają tego samego indexu, dane się mieszają

**Rozwiązanie Option A (Separate indexes):**
```python
# preprocessor/indexing/elasticsearch.py
index_name = f"{series_name.lower()}_segments"  # Np: "ranczo_segments", "kiepscy_segments"
```

**Rozwiązanie Option B (Shared index with series field):**
```python
# Jeden index "all_segments" z polem:
{
  "series_name": "kiepscy",
  "season": 1,
  "episode": 5,
  ...
}
# Query musi filtrować po series_name
```

**REKOMENDACJA:** Option B - łatwiejsze multi-series search w bocie.

### Problem 4: Docker volume permissions
**Symptom:** `Permission denied` przy tworzeniu `/output_data/{series_name}/`

**Rozwiązanie:**
```bash
# Upewnij się, że user w kontenerze ma write permissions
chmod -R 777 preprocessor/output_data/  # Development only!
# Lub lepiej: chown do właściwego UID:GID
```

### Problem 5: Episode metadata JSON location - bot nie znajduje plików
**Symptom:** Bot szuka `ranczo_episodes.json` w `/app/output_data/` ale plik jest w `/app/output_data/ranczo/`

**Rozwiązanie:**
- Zaktualizuj bot config aby wskazywał na `{series_name}_episodes.json` w nowej lokalizacji
- Lub: symlink ze starej lokalizacji do nowej

```bash
ln -s output_data/ranczo/ranczo_episodes.json output_data/ranczo_episodes.json
```

### Problem 6: Glob patterns nie znajdują plików
**Symptom:** `_create_video_processing_items()` zwraca pustą listę

**Debug:**
```python
print(f"Scanning: {source_path}")
print(f"Pattern: {pattern}")
print(f"Files found: {list(source_path.glob(pattern))}")
```

**Rozwiązanie:**
- Sprawdź czy `source_path` poprawnie wskazuje na `/input_data/{series_name}/`
- Sprawdź czy pattern `**/*.mp4` jest prawidłowy
- Sprawdź permissions na katalogach

---

## 8. WPŁYW NA BOT

### 8.1 Bot Video Path Format

**Obecnie (preprocessor/core/output_path_builder.py:50):**
```python
path = Path("bot") / f"{series_name.upper()}-WIDEO" / season_dir_name / filename
# Przykład: "bot/RANCZO-WIDEO/S01/ranczo_s01e01.mp4"
```

**Po zmianach:**
- Preprocessor tworzy: `/output_data/ranczo/transcoded_videos/S01/ranczo_s01e01.mp4`
- Elasticsearch document `video_path`: `"bot/RANCZO-WIDEO/S01/ranczo_s01e01.mp4"`
- Bot potrzebuje mapping: `"RANCZO-WIDEO"` → `/path/to/output_data/ranczo/transcoded_videos/`

### 8.2 Zmiany w bocie (rekomendowane)

#### Option A: Mapping w bot config
```python
# bot/config.py lub podobny
SERIES_VIDEO_PATHS = {
    "ranczo": "/app/bot_videos/ranczo/transcoded_videos",
    "kiepscy": "/app/bot_videos/kiepscy/transcoded_videos",
}

def resolve_video_path(es_video_path: str) -> Path:
    # "bot/RANCZO-WIDEO/S01/ranczo_s01e01.mp4"
    # -> "/app/bot_videos/ranczo/transcoded_videos/S01/ranczo_s01e01.mp4"

    parts = Path(es_video_path).parts  # ('bot', 'RANCZO-WIDEO', 'S01', 'ranczo_s01e01.mp4')
    series_key = parts[1].replace("-WIDEO", "").lower()  # "ranczo"
    relative_path = Path(*parts[2:])  # S01/ranczo_s01e01.mp4

    return Path(SERIES_VIDEO_PATHS[series_key]) / relative_path
```

#### Option B: Zmień format video_path w ES
```python
# Zamiast: "bot/RANCZO-WIDEO/S01/ranczo_s01e01.mp4"
# Użyj: "ranczo/transcoded_videos/S01/ranczo_s01e01.mp4"

# W bocie:
video_path = Path("/app/bot_videos") / es_document["video_path"]
```

**REKOMENDACJA:** Option B - prostsze, bardziej przejrzyste.

---

## 9. CHECKLIST IMPLEMENTACJI

### Core Infrastructure
- [ ] `preprocessor/config/config.py` - `get_base_output_dir()`, `get_output_path()`
- [ ] `preprocessor/core/output_path_builder.py` - wszystkie 10 metod z `series_name`
- [ ] `preprocessor/core/base_processor.py` - input validation

### Video Processors
- [ ] `preprocessor/video/transcoder.py`
- [ ] `preprocessor/video/frame_exporter.py`
- [ ] `preprocessor/video/scene_detector.py`
- [ ] `preprocessor/video/base_video_processor.py`

### Transcription Processors
- [ ] `preprocessor/transcription/generator.py`
- [ ] `preprocessor/transcription/elevenlabs.py`
- [ ] `preprocessor/transcription/processors/sound_separator.py`

### Embeddings & Indexing
- [ ] `preprocessor/embeddings/embedding_generator.py`
- [ ] `preprocessor/embeddings/episode_name_embedder.py`
- [ ] `preprocessor/indexing/elastic_document_generator.py`
- [ ] `preprocessor/indexing/archive_generator.py`
- [ ] `preprocessor/indexing/elasticsearch.py` (index naming)

### CLI Commands
- [ ] `preprocessor/cli/commands/run_all.py`
- [ ] `preprocessor/cli/commands/transcode.py`
- [ ] `preprocessor/cli/commands/transcribe.py`
- [ ] `preprocessor/cli/commands/transcribe_elevenlabs.py`
- [ ] `preprocessor/cli/commands/index.py`
- [ ] `preprocessor/cli/commands/generate_archives.py`
- [ ] `preprocessor/cli/commands/embed.py`
- [ ] `preprocessor/cli/commands/scrape_episodes.py`
- [ ] `preprocessor/cli/commands/scrape_characters.py`

### Pipeline
- [ ] `preprocessor/cli/pipeline/steps.py` - wszystkie 13 funkcji `run_*_step()`
- [ ] `preprocessor/cli/pipeline/orchestrator.py` (jeśli potrzebne)

### Characters
- [ ] `preprocessor/characters/detector.py`
- [ ] `preprocessor/characters/reference_downloader.py`
- [ ] `preprocessor/characters/reference_processor.py`

### Scrapers
- [ ] `preprocessor/scraping/episode_scraper.py`
- [ ] `preprocessor/scraping/character_scraper.py`

### Utilities
- [ ] `preprocessor/validation/validator.py`
- [ ] `preprocessor/text_analysis/text_analyzer.py`
- [ ] `preprocessor/hashing/*` (jeśli używa output paths)

### Code Review
- [ ] Grep po hardcoded `"/app/output_data"`
- [ ] Grep po hardcoded `"output_data/"`
- [ ] Grep po `Path("output_data")`
- [ ] Sprawdź wszystkie `BASE_OUTPUT_DIR` references

### Documentation
- [ ] `preprocessor/README.md` - nowe przykłady
- [ ] Migration guide dla istniejących użytkowników
- [ ] Troubleshooting section
- [ ] `.claude/app_logic_notes.md` - zaktualizuj logic notes

### Testing
- [ ] Unit tests - ścieżki
- [ ] Integration tests - pojedyncze processory
- [ ] Test akceptacyjny 1 - nowa seria
- [ ] Test akceptacyjny 2 - dwie serie jednocześnie
- [ ] Test akceptacyjny 3 - migration error message
- [ ] Performance test - czy nie ma degradacji

---

## 10. ESTYMACJA CZASU

| Faza | Czas | Priorytet |
|------|------|-----------|
| Faza 1: Core Infrastructure | 1-2 dni | KRYTYCZNY ⚠️ |
| Faza 2: Video & Transcription | 2-3 dni | WYSOKI 🔴 |
| Faza 3: Embeddings & Indexing | 1-2 dni | WYSOKI 🔴 |
| Faza 4: CLI & Pipeline | 1 dzień | ŚREDNI 🟡 |
| Faza 5: Characters, Scrapers, Utils | 1 dzień | ŚREDNI 🟡 |
| Faza 6: Documentation & Testing | 1 dzień | NISKI 🟢 |
| **TOTAL** | **7-10 dni** | |

**Uwaga:** To estymacja dla doświadczonego developera pracującego full-time. Może się różnić w zależności od:
- Znajomości codebase
- Liczby edge cases
- Liczby bugów do fixowania
- Complexity testów

---

## 11. PRZYKŁADY UŻYCIA (PO IMPLEMENTACJI)

### Przykład 1: Processing nowej serii (Kiepscy)

```bash
# 1. Przygotuj strukturę katalogów
mkdir -p preprocessor/input_data/kiepscy/S01
mkdir -p preprocessor/input_data/kiepscy/S02

# 2. Przekopiuj i przemianuj pliki (już zrobione wcześniej)
# Pliki: S01E001.Title.mp4, S01E002.Title.mp4, ...

# 3. Uruchom preprocessing
./run-preprocessor.sh run-all /input_data/kiepscy \
  --series-name kiepscy \
  --scrape-urls https://pl.wikipedia.org/wiki/Lista_odcinków_serialu_Świat_według_Kiepskich \
  --character-urls https://pl.wikipedia.org/wiki/Lista_postaci_serialu_Świat_według_Kiepskich \
  --parser-mode premium \
  --search-mode premium

# 4. Wyniki znajdziesz w:
#    preprocessor/output_data/kiepscy/transcoded_videos/
#    preprocessor/output_data/kiepscy/transcriptions/
#    preprocessor/output_data/kiepscy/elastic_documents/
#    preprocessor/output_data/kiepscy/kiepscy_episodes.json
```

### Przykład 2: Processing wielu serii równolegle

```bash
# Terminal 1: Ranczo
./run-preprocessor.sh run-all /input_data/ranczo --series-name ranczo &

# Terminal 2: Kiepscy
./run-preprocessor.sh run-all /input_data/kiepscy --series-name kiepscy &

# Terminal 3: M jak miłość
./run-preprocessor.sh run-all /input_data/mjakmilosc --series-name mjakmilosc &

# Dane są całkowicie izolowane, każdy serial w swoim folderze
```

### Przykład 3: Resumowanie przerwanego processingu

```bash
# Processing przerwany (Ctrl+C lub crash)
./run-preprocessor.sh run-all /input_data/kiepscy --series-name kiepscy
# ^C (interrupted)

# Resume od miejsca przerwania
./run-preprocessor.sh run-all /input_data/kiepscy --series-name kiepscy
# State manager automatically resumes from /output_data/kiepscy/processing_metadata/state.json
```

### Przykład 4: Processing tylko wybranych kroków

```bash
# Skip transcoding (już masz transcoded videos)
./run-preprocessor.sh run-all /input_data/kiepscy \
  --series-name kiepscy \
  --skip-transcode

# Skip wszystko oprócz indexing
./run-preprocessor.sh run-all /input_data/kiepscy \
  --series-name kiepscy \
  --skip-transcode \
  --skip-transcribe \
  --skip-scenes \
  --skip-frame-export \
  --skip-embeddings \
  --skip-elastic-documents \
  --skip-archives \
  --skip-validation
```

---

## 12. 5 NAJWAŻNIEJSZYCH PLIKÓW DO ZMIANY

1. **`preprocessor/config/config.py`**
   - Centralna definicja `BASE_OUTPUT_DIR` i wszystkich settings
   - To jest **serce systemu ścieżek**
   - Zmiana: `get_base_output_dir(series_name)` function

2. **`preprocessor/core/output_path_builder.py`**
   - Wszystkie metody budowania ścieżek output
   - Używane przez **każdy processor**
   - Zmiana: dodaj `series_name` param do 10 metod

3. **`preprocessor/core/base_processor.py`**
   - Metoda `_create_video_processing_items()` - skanowanie input files
   - Walidacja struktury katalogów
   - Zmiana: input path validation + auto-append `series_name`

4. **`preprocessor/cli/commands/run_all.py`**
   - Główny entry point pipeline'u
   - Definicje default paths
   - Orchestracja wszystkich kroków
   - Zmiana: default paths z `get_base_output_dir(series_name)`

5. **`preprocessor/cli/pipeline/steps.py`**
   - Wszystkie funkcje `run_*_step()` które inicjalizują processory
   - Przekazują ścieżki do każdego komponentu
   - Zmiana: przekaż `series_name` do wszystkich processorów

---

## 13. NOTATKI KOŃCOWE

### Co działa dobrze w obecnym designie?
✅ Modularność - każdy processor jest osobny
✅ Używanie `OutputPathBuilder` - centralne zarządzanie ścieżkami
✅ State manager - resume po przerwaniu
✅ Docker isolation - łatwe deployment

### Co będzie lepsze po zmianach?
✅ Multi-series support - wiele seriali w jednym środowisku
✅ Pełna izolacja danych między serialami
✅ Przejrzysta struktura katalogów
✅ Łatwiejsze zarządzanie i czyszczenie danych
✅ Możliwość równoległego processingu wielu seriali

### Ryzyka i mitigacje
⚠️ **Ryzyko:** Dużo plików do zmiany (40+ files)
   **Mitigacja:** Stopniowa implementacja, testy po każdej fazie

⚠️ **Ryzyko:** Breaking changes dla istniejących setupów
   **Mitigacja:** Jasny error message + migration guide

⚠️ **Ryzyko:** Hardcoded paths w nieoczekiwanych miejscach
   **Mitigacja:** Comprehensive grep + code review

⚠️ **Ryzyko:** Wpływ na bot (video paths)
   **Mitigacja:** Zaktualizuj bot config + symlinki (tymczasowo)

---

## KONIEC PLANU

**Status:** ✅ PLAN GOTOWY - CZEKA NA IMPLEMENTACJĘ

**Next steps:**
1. Review planu z zespołem
2. Zatwierdzenie podejścia (strict mode vs auto-migration)
3. Rozpoczęcie implementacji od Fazy 1
4. Testy po każdej fazie

**Pytania? Problemy?**
- Sprawdź sekcję 7: "Potencjalne problemy i rozwiązania"
- Zajrzyj do sekcji 8: "Wpływ na bot"
- Skonsultuj z zespołem przed zmianami w core files

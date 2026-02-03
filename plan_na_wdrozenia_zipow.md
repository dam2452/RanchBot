# Kompletny Plan: Multi-Serial System z Reindexowaniem z Zipów

> **Data utworzenia:** 2026-02-02
> **Projekt:** RanchBot Multi-Serial Migration
> **Szacowany czas implementacji:** 23-30 godzin
> **Status:** Gotowy do implementacji

---

## Spis Treści

1. [Kontekst i Wymagania](#1-kontekst-i-wymagania)
2. [Wyniki Eksploracji Kodu](#2-wyniki-eksploracji-kodu)
3. [Architektura Rozwiązania](#3-architektura-rozwiązania)
4. [Baza Danych](#4-baza-danych)
5. [Nowe Moduły - Pełny Kod](#5-nowe-moduły---pełny-kod)
6. [Modyfikacje Istniejących Plików](#6-modyfikacje-istniejących-plików)
7. [Testy](#7-testy)
8. [Dokumentacja](#8-dokumentacja)
9. [Sekwencja Implementacji](#9-sekwencja-implementacji)
10. [Weryfikacja](#10-weryfikacja)

---

## 1. Kontekst i Wymagania

### 1.1 Obecny Stan

**RanchBot** to bot Telegram do zarządzania klipami wideo z serialu "Ranczo":
- Single-serial system
- Dane w Elasticsearch (7 indeksów)
- Pliki MP4 w `bot/RANCZO-WIDEO/`
- Ścieżki hardcoded

### 1.2 Cel Migracji

Przekształcenie w **multi-serial system** z:
1. Kontekstem użytkownika (aktywny serial)
2. Zipami jako źródłem prawdy dla Elasticsearch
3. Komendą admin do reindexowania
4. Nową strukturą plików MP4

### 1.3 Wymagania Użytkownika

#### Dane w Zipach (Źródło Prawdy)
- Lokalizacja: `preprocessor/output_data/archives/{SEASON}/{EPISODE}/{series}_{CODE}_elastic_documents.zip`
- Przykład: `preprocessor/output_data/archives/S01/E01/ranczo_S01E01_elastic_documents.zip`
- Zawartość zipa (8 plików JSONL):
  ```
  *_text_segments.jsonl
  *_text_embeddings.jsonl
  *_video_frames.jsonl
  *_episode_name.jsonl
  *_text_statistics.jsonl
  *_full_episode_embedding.jsonl
  *_sound_events.jsonl
  *_sound_event_embeddings.jsonl
  ```

#### Nowa Struktura MP4
- Lokalizacja: `preprocessor/output_data/transcoded_videos/{SEASON}/{series}_{CODE}.mp4`
- Przykład: `preprocessor/output_data/transcoded_videos/S01/ranczo_S01E01.mp4`
- **Problem:** Stare dokumenty mają `video_path: "bot/RANCZO-WIDEO/S01/..."`

#### System Multi-Serialowy
- Domyślny kontekst: `"ranczo"`
- Komenda `/serial [nazwa]` - zmiana kontekstu
- Wszystkie wyszukiwania w ramach aktywnego serialu
- Identyfikacja: kod odcinka (S01E13) + series_name w metadanych

#### Komenda Reindexowania (Admin Only)
- `/reindex all` - reindexuj wszystkie seriale
- `/reindex all-new` - tylko seriale bez indeksów w Elasticu
- `/reindex [serial_name]` - konkretny serial (nadpisuje)
- **Proces:**
  1. Skanowanie folderów (zipy + mp4)
  2. Rozpakowywanie zipów **realtime do pamięci** (BytesIO)
  3. Bulk load do Elasticsearch
  4. Aktualizacja `video_path`

#### Wymagania Techniczne
- ✅ SOLID + DRY (bez duplikacji kodu)
- ✅ Kod samoopisujący się
- ✅ Dokumentacja (.md, COMMANDS, help, REST API)
- ✅ Komendy przez Telegram + REST
- ✅ Sezon 0 traktowany normalnie

---

## 2. Wyniki Eksploracji Kodu

### 2.1 Elasticsearch (Agent a6c9839)

#### 7 Indeksów Per Serial

| Indeks | Suffix | Typ Dokumentu | Przeznaczenie |
|--------|--------|---------------|---------------|
| `{name}_segments` | `text_segments` | Segmenty transkrypcji | Full-text search (BM25) |
| `{name}_text_embeddings` | `text_embeddings` | Text embeddings | Semantic search (4096D) |
| `{name}_video_frames` | `video_frames` | Video embeddings + metadata | Visual search + characters + objects |
| `{name}_episode_names` | `episode_names` | Title embeddings | Semantic search po tytułach |
| `{name}_full_episode_embeddings` | `full_episode_embeddings` | Full episode embeddings | Całościowy embedding odcinka |
| `{name}_sound_events` | `sound_events` | Sound event metadata | Wyszukiwanie po zdarzeniach dźwiękowych |
| `{name}_sound_event_embeddings` | `sound_event_embeddings` | Sound event embeddings | Semantic search po audio |

#### Struktura Dokumentu text_segments

```json
{
  "episode_id": "S01E01",
  "episode_metadata": {
    "season": 1,
    "episode_number": 1,
    "title": "Spadek",
    "premiere_date": "05.03.2006",
    "series_name": "ranczo",
    "viewership": "4396564"
  },
  "segment_id": 0,
  "text": "What a beautiful city.",
  "start_time": 69.19,
  "end_time": 71.42,
  "speaker": "unknown",
  "video_path": "bot/RANCZO-WIDEO/S01/ranczo_S01E01.mp4",
  "scene_info": {
    "scene_number": 5,
    "scene_start_time": 44.68,
    "scene_end_time": 70.4,
    "scene_start_frame": 1117,
    "scene_end_frame": 1760
  }
}
```

#### Bulk Indexing

Plik: `preprocessor/indexing/elasticsearch.py` (linie 200-216)

```python
await async_bulk(
    self.client,
    actions,
    chunk_size=50,
    max_chunk_bytes=5 * 1024 * 1024,  # 5MB
)
```

Format akcji:
```python
{
  "_index": "ranczo_segments",
  "_source": {document data}
}
```

#### Mappings

Plik: `preprocessor/search/elastic_manager.py` (linie 14-376)

**Text Segments Mapping:**
```python
SEGMENTS_INDEX_MAPPING = {
  "mappings": {
    "properties": {
      "episode_id": {"type": "keyword"},
      "episode_metadata": {
        "properties": {
          "season": {"type": "integer"},
          "episode_number": {"type": "integer"},
          "title": {"type": "text"},
          "premiere_date": {"type": "keyword"},
          "series_name": {"type": "keyword"},  # WAŻNE!
          "viewership": {"type": "keyword"}
        }
      },
      "segment_id": {"type": "integer"},
      "text": {"type": "text"},
      "start_time": {"type": "float"},
      "end_time": {"type": "float"},
      "speaker": {"type": "keyword"},
      "video_path": {"type": "keyword"},
      "scene_info": { ... }
    }
  }
}
```

### 2.2 Bot Commands (Agent adad82b)

#### 5 Poziomów Uprawnień

1. **Admin** (`AdminPermissionLevelFactory`)
   - `/addkey`, `/removekey`, `/listkeys`
   - `/addwhitelist`, `/removewhitelist`
   - `/addsub`, `/removesub`

2. **Moderator** (`ModeratorPermissionLevelFactory`)
   - `/admin`, `/listadmins`, `/listmoderators`, `/listwhitelist`
   - `/transcription`, `/updatenote`

3. **Subscribed** (`SubscribedPermissionLevelFactory`)
   - `/clip`, `/search`, `/compile`, `/myclips`, `/save`, `/delete`, `/report`
   - **GŁÓWNE FUNKCJE BOTA**

4. **Whitelisted** (`WhitelistedPermissionLevelFactory`)
   - `/start`, `/help`, `/substatus`

5. **Any User** (`AnyUserPermissionLevelFactory`)
   - `/savekey`

#### Rejestracja Komend

**Telegram:**
```python
# factory/permission_level_factory.py (linie 39-50)
for handler in self.get_telegram_handlers():
    for command in handler.get_commands():
        dp.message.register(handler_fn, Command(commands=[command]))
```

**REST API:**
```python
# platforms/rest_runner.py (linie 185-243)
@api_router.post("/{command_name}")
async def universal_handler(command_name: str, ...):
    handler_cls = command_handlers.get(command_name)
    if not handler_cls:
        raise HTTPException(404, "Unknown command")
    ...
```

#### Middleware

**Rate Limiting:**
- Non-admin/moderator: max 5 komend / 30 sekund
- Admins/moderatorzy: bez limitów

**Permission Checks:**
```python
# bot/middlewares/bot_middleware.py
async def check(self, message):
    if command in self._supported_commands:
        if await self.check_permission(message):  # np. is_user_admin()
            await handler()
        else:
            await responder.send_text("❌ Brak uprawnień ❌")
```

### 2.3 Video Handling (Agent a1c8c98)

#### Problem Video Path

**W Elasticu:**
```
"video_path": "bot/RANCZO-WIDEO/S01/ranczo_S01E01.mp4"
```

**Rzeczywista lokalizacja:**
```
/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/output_data/transcoded_videos/S01/ranczo_S01E01.mp4
```

**Brak walidacji!** FFmpeg failuje jeśli plik nie istnieje.

#### Ekstraktowanie Klipów

Plik: `bot/video/clips_extractor.py` (linia 33)

```python
output_filename = await ClipsExtractor.extract_clip(
    segment["video_path"],  # Pobrane z Elasticsearch
    start_time,
    end_time,
    logger
)
```

Bezpośrednio przekazuje ścieżkę do FFmpeg:
```python
"-i", str(video_path),
```

---

## 3. Architektura Rozwiązania

### 3.1 Diagram ASCII - Pełna Architektura

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER INTERACTION LAYER                          │
├────────────────────────────────┬────────────────────────────────────────┤
│     Telegram Bot               │         REST API (FastAPI)             │
│  - /serial [nazwa]             │  - POST /api/v1/serial                 │
│  - /reindex [target]           │  - POST /api/v1/reindex                │
│  - /klip, /szukaj, etc.        │  - POST /api/v1/{command}              │
└────────────────┬───────────────┴────────────┬───────────────────────────┘
                 │                            │
                 └────────────┬───────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────────────┐
│                     HANDLER LAYER (aiogram)                            │
├────────────────────────────────────────────────────────────────────────┤
│  AdminPermissionLevelFactory:                                          │
│    - ReindexHandler (NEW)                                              │
│                                                                         │
│  SubscribedPermissionLevelFactory:                                     │
│    - SerialContextHandler (NEW)                                        │
│    - ClipHandler, SearchHandler (MODIFIED - context injection)         │
│                                                                         │
│  SerialContextMiddleware (NEW):                                        │
│    - Inject active_series to all queries                              │
└────────────────────────────────┬───────────────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────────────┐
│                    BUSINESS LOGIC LAYER                                │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ReindexService (NEW):                                                 │
│    - scan_series_directories()                                         │
│    - detect_series_from_filename()                                     │
│    - reindex_series(series_name)                                       │
│    - reindex_all() / reindex_all_new()                                 │
│                                                                         │
│  ZipExtractor (NEW):                                                   │
│    - extract_to_memory(zip_path) → Dict[str, BytesIO]                  │
│    - parse_jsonl_from_memory(content) → List[Dict]                     │
│                                                                         │
│  VideoPathTransformer (NEW):                                           │
│    - transform_video_path(doc) → updated_doc                           │
│    - validate_mp4_exists(path) → bool                                  │
│                                                                         │
│  ElasticBulkIndexer (MODIFIED):                                        │
│    - bulk_index_documents(series_name, documents, index_type)          │
│    - delete_series_indices(series_name)                                │
│                                                                         │
│  SerialContextManager (NEW):                                           │
│    - get_user_active_series(user_id) → str                             │
│    - set_user_active_series(user_id, series_name)                      │
│    - list_available_series() → List[str]                               │
│                                                                         │
│  TranscriptionFinder (MODIFIED):                                       │
│    - All methods now filter by episode_metadata.series_name            │
│                                                                         │
└────────────────────────────────┬───────────────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────────────┐
│                       DATA ACCESS LAYER                                │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  DatabaseManager (MODIFIED):                                           │
│    - get_user_active_series(user_id) → str                             │
│    - set_user_active_series(user_id, series_name)                      │
│    - (NEW TABLE: user_series_context)                                  │
│                                                                         │
│  ElasticSearchManager (MODIFIED):                                      │
│    - All queries add filter: {"term": {"episode_metadata.series_name"}}│
│    - Index naming: {series_name}_{index_type}                          │
│                                                                         │
└────────────────────────────────┬───────────────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────────────┐
│                       STORAGE LAYER                                    │
├─────────────────────────────────┬──────────────────────────────────────┤
│  PostgreSQL                     │  Elasticsearch                       │
│  - user_series_context (NEW)   │  - {series}_segments                 │
│  - user_profiles                │  - {series}_text_embeddings          │
│  - user_roles                   │  - {series}_video_frames             │
│  - video_clips                  │  - {series}_episode_names            │
│  - search_history               │  - {series}_full_episode_embeddings  │
│  - last_clips                   │  - {series}_sound_events             │
│                                 │  - {series}_sound_event_embeddings   │
└─────────────────────────────────┴──────────────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────────────┐
│                     FILE SYSTEM LAYER                                  │
├────────────────────────────────────────────────────────────────────────┤
│  preprocessor/output_data/                                             │
│    archives/{SEASON}/{EPISODE}/{series}_{CODE}_elastic_documents.zip  │
│    transcoded_videos/{SEASON}/{series}_{CODE}.mp4                      │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Proces Reindexowania - Flow Diagram

```
                ┌──────────────────────┐
                │ Admin: /reindex all  │
                └──────────┬───────────┘
                           │
                ┌──────────▼──────────────────────┐
                │   ReindexHandler                │
                │  - validate arguments           │
                │  - create progress callback     │
                └──────────┬──────────────────────┘
                           │
                ┌──────────▼──────────────────────┐
                │   ReindexService                │
                │  - reindex_all()                │
                │  - reindex_all_new()            │
                │  - reindex_series(name)         │
                └──────────┬──────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
  ┌─────▼──────┐   ┌──────▼────────┐   ┌────▼──────┐
  │SeriesScanner│   │ ZipExtractor  │   │VideoPath  │
  │            │   │               │   │Transformer│
  │- scan_all()│   │- extract_to_  │   │- transform│
  │- scan_zips │   │  memory()     │   │- validate │
  │- scan_mp4s │   │- parse_jsonl()│   │           │
  └─────┬──────┘   └──────┬────────┘   └────┬──────┘
        │                 │                  │
        │  ┌──────────────▼──────────────┐   │
        │  │  For Each Episode:          │   │
        │  │  1. Extract zip to memory   │   │
        │  │  2. Parse JSONL files       │◄──┘
        │  │  3. Transform video_path    │
        │  │  4. Bulk index to ES        │
        │  └──────────────┬──────────────┘
        │                 │
        └─────────────────▼──────────────────┐
                    ┌─────────────────────────▼──┐
                    │  ElasticSearchManager      │
                    │  - delete_indices()        │
                    │  - create_indices()        │
                    │  - async_bulk()            │
                    └─────────────────────────────┘
                               │
                    ┌──────────▼─────────────┐
                    │ Progress Callback      │
                    │ (throttled 1 msg / 2s) │
                    └────────────────────────┘
```

### 3.3 Serial Context Injection - Flow Diagram

```
┌────────────────────────────────────────┐
│  User executes: /klip cytat            │
└──────────────┬─────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  SerialContextMiddleware                │
│  1. Extract user_id from message       │
│  2. Call SerialContextManager           │
│  3. Get active_series from DB           │
│  4. Inject into data["active_series"]  │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  ClipHandler.handle()                   │
│  1. Extract active_series from state    │
│  2. Pass to TranscriptionFinder         │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  TranscriptionFinder.find_segment_by_   │
│  quote(quote, logger, active_series)    │
│  1. Build index name: {series}_segments │
│  2. Add filter: series_name == active   │
│  3. Execute Elasticsearch query         │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  Elasticsearch                          │
│  Query: {                               │
│    "index": "ranczo_segments",          │
│    "query": {                           │
│      "bool": {                          │
│        "must": [...],                   │
│        "filter": [                      │
│          {"term": {"episode_metadata.  │
│                    series_name": "ranczo│
│        }}]                              │
│      }                                  │
│    }                                    │
│  }                                      │
└─────────────────────────────────────────┘
```

---

## 4. Baza Danych

### 4.1 Nowa Tabela: user_series_context

```sql
CREATE TABLE IF NOT EXISTS user_series_context (
    user_id BIGINT PRIMARY KEY REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    active_series VARCHAR(50) NOT NULL DEFAULT 'ranczo',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_series_name CHECK (active_series ~ '^[a-z0-9_-]+$')
);

CREATE INDEX IF NOT EXISTS idx_user_series_context_user_id
    ON user_series_context(user_id);
CREATE INDEX IF NOT EXISTS idx_user_series_context_active_series
    ON user_series_context(active_series);
```

### 4.2 Trigger: Auto-Update Timestamp

```sql
CREATE OR REPLACE FUNCTION update_series_context_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_series_context_timestamp
BEFORE UPDATE ON user_series_context
FOR EACH ROW
EXECUTE FUNCTION update_series_context_timestamp();
```

### 4.3 Trigger: Auto-Create Context for New Users

```sql
CREATE OR REPLACE FUNCTION ensure_user_series_context()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO user_series_context (user_id, active_series)
    VALUES (NEW.user_id, 'ranczo')
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_ensure_user_series_context
AFTER INSERT ON user_profiles
FOR EACH ROW
EXECUTE FUNCTION ensure_user_series_context();
```

### 4.4 Migracja Istniejących Użytkowników

```sql
INSERT INTO user_series_context (user_id, active_series)
SELECT user_id, 'ranczo'
FROM user_profiles
ON CONFLICT (user_id) DO NOTHING;
```

### 4.5 Model Dataclass

Plik: `bot/database/models.py`

```python
from dataclasses import dataclass
from datetime import datetime
from bot.interfaces.serializable import Serializable


@dataclass
class SeriesContext(Serializable):
    user_id: int
    active_series: str
    last_updated: datetime
```

---

## 5. Nowe Moduły - Pełny Kod

### 5.1 bot/handlers/administration/reindex_handler.py

```python
import logging
import time
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.services.reindex.reindex_service import ReindexService
from bot.responses.administration.reindex_handler_responses import (
    get_reindex_usage_message,
    get_reindex_started_message,
    get_reindex_progress_message,
    get_reindex_complete_message,
    get_reindex_error_message,
)


class ReindexHandler(BotMessageHandler):
    def __init__(self, message, responder, logger):
        super().__init__(message, responder, logger)
        self.reindex_service = ReindexService(logger)
        self.last_progress_time = 0

    def get_commands(self) -> List[str]:
        return ["reindex", "ridx"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
            self.__check_target_valid,
        ]

    async def __check_argument_count(self) -> bool:
        return await self._validate_argument_count(
            self._message, 1, get_reindex_usage_message()
        )

    async def __check_target_valid(self) -> bool:
        args = self._message.get_text().split()
        target = args[1]

        if target in ["all", "all-new"]:
            return True

        if not target.replace('_', '').replace('-', '').isalnum():
            await self.reply_error(get_reindex_usage_message())
            return False

        return True

    async def _do_handle(self) -> None:
        args = self._message.get_text().split()
        target = args[1]

        await self.reply(get_reindex_started_message(target))

        progress_callback = self._create_progress_callback()

        try:
            if target == "all":
                results = await self.reindex_service.reindex_all(progress_callback)
                total_docs = sum(r.documents_indexed for r in results)
                total_eps = sum(r.episodes_processed for r in results)
                await self.reply(
                    f"Reindex complete! Series: {len(results)}, "
                    f"Episodes: {total_eps}, Documents: {total_docs}"
                )
            elif target == "all-new":
                results = await self.reindex_service.reindex_all_new(progress_callback)
                if not results:
                    await self.reply("No new series to reindex.")
                    return
                total_docs = sum(r.documents_indexed for r in results)
                total_eps = sum(r.episodes_processed for r in results)
                await self.reply(
                    f"Reindex complete! New series: {len(results)}, "
                    f"Episodes: {total_eps}, Documents: {total_docs}"
                )
            else:
                result = await self.reindex_service.reindex_series(
                    target, progress_callback
                )
                await self.reply(get_reindex_complete_message(result))

            await self._log_system_message(
                logging.INFO,
                f"Reindex complete for target: {target}"
            )
        except Exception as e:
            await self.reply_error(get_reindex_error_message(str(e)))
            await self._log_system_message(
                logging.ERROR,
                f"Reindex failed: {e}",
                exc_info=True
            )

    def _create_progress_callback(self):
        async def callback(message: str, current: int, total: int):
            now = time.time()

            if now - self.last_progress_time < 2:
                return

            self.last_progress_time = now

            await self.reply(get_reindex_progress_message(message, current, total))

        return callback
```

### 5.2 bot/handlers/not_sending_videos/serial_context_handler.py

```python
import logging
from typing import List

from bot.handlers.bot_message_handler import (
    BotMessageHandler,
    ValidatorFunctions,
)
from bot.services.serial_context.serial_context_manager import SerialContextManager
from bot.responses.not_sending_videos.serial_context_handler_responses import (
    get_serial_usage_message,
    get_serial_changed_message,
    get_serial_invalid_message,
    get_serial_current_message,
)


class SerialContextHandler(BotMessageHandler):
    def __init__(self, message, responder, logger):
        super().__init__(message, responder, logger)
        self.serial_manager = SerialContextManager(logger)

    def get_commands(self) -> List[str]:
        return ["serial", "ser"]

    async def _get_validator_functions(self) -> ValidatorFunctions:
        return [
            self.__check_argument_count,
        ]

    async def __check_argument_count(self) -> bool:
        args = self._message.get_text().split()

        if len(args) > 2:
            await self.reply_error(get_serial_usage_message())
            return False

        return True

    async def _do_handle(self) -> None:
        args = self._message.get_text().split()
        user_id = self._message.get_user_id()

        if len(args) == 1:
            current_series = await self.serial_manager.get_user_active_series(
                user_id
            )
            await self.reply(get_serial_current_message(current_series))
            return

        series_name = args[1].lower()

        available_series = await self.serial_manager.list_available_series()
        if series_name not in available_series:
            await self.reply_error(
                get_serial_invalid_message(series_name, available_series)
            )
            return

        await self.serial_manager.set_user_active_series(user_id, series_name)

        await self.reply(get_serial_changed_message(series_name))
        await self._log_system_message(
            logging.INFO,
            f"User {user_id} changed series to: {series_name}"
        )
```

### 5.3 bot/middlewares/serial_context_middleware.py

```python
import logging
from typing import Any, Callable

from aiogram import types
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from bot.services.serial_context.serial_context_manager import SerialContextManager


class SerialContextMiddleware(BaseMiddleware):
    def __init__(self, logger: logging.Logger):
        super().__init__()
        self.logger = logger
        self.serial_manager = SerialContextManager(logger)

    async def __call__(
        self,
        handler: Callable,
        event: types.Message,
        data: dict
    ) -> Any:
        user_id = event.from_user.id

        active_series = await self.serial_manager.get_user_active_series(user_id)

        data["active_series"] = active_series

        self.logger.debug(f"User {user_id} active series: {active_series}")

        return await handler(event, data)
```

### 5.4 bot/services/reindex/reindex_service.py

```python
import logging
from pathlib import Path
from typing import Callable, Awaitable, List, Dict, Optional
from dataclasses import dataclass

from bot.services.reindex.series_scanner import SeriesScanner
from bot.services.reindex.zip_extractor import ZipExtractor
from bot.services.reindex.video_path_transformer import VideoPathTransformer
from preprocessor.search.elastic_manager import ElasticSearchManager


@dataclass
class ReindexResult:
    series_name: str
    episodes_processed: int
    documents_indexed: int
    errors: List[str]

    @property
    def summary(self) -> str:
        error_str = f", {len(self.errors)} errors" if self.errors else ""
        return (
            f"Series: {self.series_name}, "
            f"Episodes: {self.episodes_processed}, "
            f"Documents: {self.documents_indexed}"
            f"{error_str}"
        )


class ReindexService:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.scanner = SeriesScanner(logger)
        self.zip_extractor = ZipExtractor(logger)
        self.video_transformer = VideoPathTransformer(logger)
        self.es_manager: Optional[ElasticSearchManager] = None

    async def _init_elasticsearch(self):
        if self.es_manager is None:
            from bot.settings import settings
            self.es_manager = await ElasticSearchManager.connect_to_elasticsearch(
                settings.ES_HOST,
                settings.ES_USER,
                settings.ES_PASS.get_secret_value(),
                self.logger
            )

    async def reindex_all(
        self,
        progress_callback: Callable[[str, int, int], Awaitable[None]]
    ) -> List[ReindexResult]:
        await self._init_elasticsearch()

        all_series = self.scanner.scan_all_series()
        results = []

        total_series = len(all_series)
        for idx, series_name in enumerate(all_series):
            await progress_callback(
                f"Processing series {idx+1}/{total_series}: {series_name}",
                idx,
                total_series
            )

            result = await self.reindex_series(series_name, progress_callback)
            results.append(result)

        return results

    async def reindex_all_new(
        self,
        progress_callback: Callable[[str, int, int], Awaitable[None]]
    ) -> List[ReindexResult]:
        await self._init_elasticsearch()

        all_series = self.scanner.scan_all_series()
        new_series = []

        for series_name in all_series:
            index_exists = await self.es_manager.indices.exists(
                index=f"{series_name}_segments"
            )
            if not index_exists:
                new_series.append(series_name)

        if not new_series:
            await progress_callback("No new series to reindex", 0, 0)
            return []

        results = []
        total_series = len(new_series)

        for idx, series_name in enumerate(new_series):
            await progress_callback(
                f"Processing new series {idx+1}/{total_series}: {series_name}",
                idx,
                total_series
            )

            result = await self.reindex_series(series_name, progress_callback)
            results.append(result)

        return results

    async def reindex_series(
        self,
        series_name: str,
        progress_callback: Callable[[str, int, int], Awaitable[None]]
    ) -> ReindexResult:
        await self._init_elasticsearch()

        await progress_callback(f"Scanning {series_name}...", 0, 100)

        zip_files = self.scanner.scan_series_zips(series_name)
        if not zip_files:
            raise ValueError(f"No zip files found for series: {series_name}")

        mp4_map = self.scanner.scan_series_mp4s(series_name)

        await progress_callback(f"Deleting old indices for {series_name}...", 5, 100)
        await self._delete_series_indices(series_name)

        total_episodes = len(zip_files)
        indexed_count = 0
        errors = []

        for idx, zip_path in enumerate(zip_files):
            try:
                episode_code = self._extract_episode_code(zip_path)
                progress_pct = 10 + int((idx / total_episodes) * 85)

                await progress_callback(
                    f"Processing {episode_code}... ({idx+1}/{total_episodes})",
                    progress_pct,
                    100
                )

                mp4_path = mp4_map.get(episode_code)

                jsonl_contents = self.zip_extractor.extract_to_memory(zip_path)

                for jsonl_type, buffer in jsonl_contents.items():
                    documents = self.zip_extractor.parse_jsonl_from_memory(buffer)

                    for doc in documents:
                        self.video_transformer.transform_video_path(doc, mp4_path)

                    index_name = self._get_index_name(series_name, jsonl_type)

                    await self._bulk_index_documents(
                        index_name,
                        jsonl_type,
                        documents
                    )

                    indexed_count += len(documents)

            except Exception as e:
                error_msg = f"Failed to process {zip_path.name}: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                errors.append(error_msg)

        await progress_callback(f"Reindex of {series_name} complete!", 100, 100)

        return ReindexResult(
            series_name=series_name,
            episodes_processed=total_episodes - len(errors),
            documents_indexed=indexed_count,
            errors=errors
        )

    async def _delete_series_indices(self, series_name: str):
        index_types = [
            "segments",
            "text_embeddings",
            "video_frames",
            "episode_names",
            "full_episode_embeddings",
            "sound_events",
            "sound_event_embeddings"
        ]

        for index_type in index_types:
            index_name = f"{series_name}_{index_type}"
            try:
                if await self.es_manager.indices.exists(index=index_name):
                    await self.es_manager.indices.delete(index=index_name)
                    self.logger.info(f"Deleted index: {index_name}")
            except Exception as e:
                self.logger.warning(f"Failed to delete index {index_name}: {e}")

    async def _bulk_index_documents(
        self,
        index_name: str,
        index_type: str,
        documents: List[Dict]
    ):
        from elasticsearch.helpers import async_bulk

        mapping = self._get_mapping_for_type(index_type)

        if not await self.es_manager.indices.exists(index=index_name):
            await self.es_manager.indices.create(
                index=index_name,
                body=mapping
            )

        actions = [
            {
                "_index": index_name,
                "_source": doc
            }
            for doc in documents
        ]

        await async_bulk(
            self.es_manager,
            actions,
            chunk_size=50,
            max_chunk_bytes=5 * 1024 * 1024
        )

        self.logger.info(f"Indexed {len(documents)} documents to {index_name}")

    def _get_mapping_for_type(self, index_type: str):
        mappings = {
            "text_segments": ElasticSearchManager.SEGMENTS_INDEX_MAPPING,
            "text_embeddings": ElasticSearchManager.TEXT_EMBEDDINGS_INDEX_MAPPING,
            "video_frames": ElasticSearchManager.VIDEO_EMBEDDINGS_INDEX_MAPPING,
            "episode_names": ElasticSearchManager.EPISODE_NAMES_INDEX_MAPPING,
            "full_episode_embeddings": ElasticSearchManager.FULL_EPISODE_EMBEDDINGS_INDEX_MAPPING,
            "sound_events": ElasticSearchManager.SOUND_EVENTS_INDEX_MAPPING,
            "sound_event_embeddings": ElasticSearchManager.SOUND_EVENT_EMBEDDINGS_INDEX_MAPPING,
        }
        return mappings.get(index_type, ElasticSearchManager.SEGMENTS_INDEX_MAPPING)

    def _get_index_name(self, series_name: str, jsonl_type: str) -> str:
        return f"{series_name}_{jsonl_type}"

    def _extract_episode_code(self, zip_path: Path) -> str:
        import re
        match = re.search(r'(S\d{2}E\d{2})', zip_path.name)
        if match:
            return match.group(1)
        return zip_path.stem
```

### 5.5 bot/services/reindex/zip_extractor.py

```python
import io
import json
import logging
import zipfile
from pathlib import Path
from typing import Dict, List


class ZipExtractor:
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def extract_to_memory(self, zip_path: Path) -> Dict[str, io.BytesIO]:
        extracted_files = {}

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for file_info in zf.infolist():
                    if not file_info.filename.endswith('.jsonl'):
                        continue

                    content = zf.read(file_info.filename)
                    buffer = io.BytesIO(content)

                    jsonl_type = self._detect_type_from_filename(file_info.filename)
                    if jsonl_type:
                        extracted_files[jsonl_type] = buffer

        except zipfile.BadZipFile as e:
            self.logger.error(f"Corrupted zip file: {zip_path}")
            raise ValueError(f"Invalid zip file: {zip_path}") from e

        return extracted_files

    def parse_jsonl_from_memory(self, buffer: io.BytesIO) -> List[Dict]:
        documents = []
        buffer.seek(0)

        for line in buffer:
            line_str = line.decode('utf-8').strip()
            if line_str:
                try:
                    doc = json.loads(line_str)
                    documents.append(doc)
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Failed to parse JSONL line: {e}")

        return documents

    def _detect_type_from_filename(self, filename: str) -> str:
        if 'text_segments' in filename:
            return 'text_segments'
        elif 'text_embeddings' in filename:
            return 'text_embeddings'
        elif 'video_frames' in filename:
            return 'video_frames'
        elif 'episode_name' in filename:
            return 'episode_names'
        elif 'full_episode_embedding' in filename:
            return 'full_episode_embeddings'
        elif 'sound_event_embeddings' in filename:
            return 'sound_event_embeddings'
        elif 'sound_events' in filename:
            return 'sound_events'
        else:
            return None
```

### 5.6 bot/services/reindex/video_path_transformer.py

```python
import logging
from pathlib import Path
from typing import Dict, Optional


class VideoPathTransformer:
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def transform_video_path(
        self,
        doc: Dict,
        mp4_path: Optional[Path]
    ) -> Dict:
        if 'video_path' not in doc:
            return doc

        if mp4_path is None:
            self.logger.warning(
                f"No MP4 path provided for document, keeping old: {doc.get('video_path')}"
            )
            return doc

        if not mp4_path.exists():
            self.logger.warning(
                f"MP4 file does not exist: {mp4_path}"
            )

        doc['video_path'] = str(mp4_path)

        return doc

    def validate_mp4_exists(self, path: str) -> bool:
        return Path(path).exists()
```

### 5.7 bot/services/reindex/series_scanner.py

```python
import logging
import re
from pathlib import Path
from typing import Dict, List


class SeriesScanner:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.archives_dir = Path("preprocessor/output_data/archives")
        self.videos_dir = Path("preprocessor/output_data/transcoded_videos")

    def scan_all_series(self) -> List[str]:
        series_set = set()

        if not self.archives_dir.exists():
            self.logger.warning(f"Archives directory does not exist: {self.archives_dir}")
            return []

        for season_dir in self.archives_dir.iterdir():
            if not season_dir.is_dir():
                continue

            for episode_dir in season_dir.iterdir():
                if not episode_dir.is_dir():
                    continue

                for zip_file in episode_dir.glob("*.zip"):
                    series_name = self._detect_series_from_filename(zip_file.name)
                    if series_name:
                        series_set.add(series_name)

        return sorted(list(series_set))

    def scan_series_zips(self, series_name: str) -> List[Path]:
        zip_files = []

        if not self.archives_dir.exists():
            return []

        for season_dir in self.archives_dir.iterdir():
            if not season_dir.is_dir():
                continue

            for episode_dir in season_dir.iterdir():
                if not episode_dir.is_dir():
                    continue

                for zip_file in episode_dir.glob(f"{series_name}_*.zip"):
                    zip_files.append(zip_file)

        return sorted(zip_files)

    def scan_series_mp4s(self, series_name: str) -> Dict[str, Path]:
        mp4_map = {}

        if not self.videos_dir.exists():
            self.logger.warning(f"Videos directory does not exist: {self.videos_dir}")
            return {}

        for season_dir in self.videos_dir.iterdir():
            if not season_dir.is_dir():
                continue

            for mp4_file in season_dir.glob(f"{series_name}_*.mp4"):
                episode_code = self._extract_episode_code(mp4_file.name)
                if episode_code:
                    mp4_map[episode_code] = mp4_file

        return mp4_map

    def _detect_series_from_filename(self, filename: str) -> str:
        match = re.match(r'^([a-z0-9_-]+)_S\d{2}E\d{2}', filename, re.IGNORECASE)
        if match:
            return match.group(1).lower()
        return None

    def _extract_episode_code(self, filename: str) -> str:
        match = re.search(r'(S\d{2}E\d{2})', filename, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return None
```

### 5.8 bot/services/serial_context/serial_context_manager.py

```python
import logging
from typing import List

from bot.database.database_manager import DatabaseManager
from bot.services.reindex.series_scanner import SeriesScanner


class SerialContextManager:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.scanner = SeriesScanner(logger)

    async def get_user_active_series(self, user_id: int) -> str:
        series = await DatabaseManager.get_user_active_series(user_id)
        return series if series else "ranczo"

    async def set_user_active_series(self, user_id: int, series_name: str) -> None:
        await DatabaseManager.set_user_active_series(user_id, series_name)
        self.logger.info(f"Set active series for user {user_id}: {series_name}")

    async def list_available_series(self) -> List[str]:
        return self.scanner.scan_all_series()
```

### 5.9 bot/responses/administration/reindex_handler_responses.py

```python
def get_reindex_usage_message() -> str:
    return (
        "Usage: /reindex [target]\n\n"
        "Targets:\n"
        "  all       - Reindex all series\n"
        "  all-new   - Reindex only series without indices\n"
        "  [series]  - Reindex specific series\n\n"
        "Example: /reindex ranczo"
    )


def get_reindex_started_message(target: str) -> str:
    return f"Starting reindex operation for: {target}"


def get_reindex_progress_message(message: str, current: int, total: int) -> str:
    if total == 0:
        return message
    percentage = int((current / total) * 100)
    return f"{message} ({percentage}%)"


def get_reindex_complete_message(result) -> str:
    error_info = ""
    if result.errors:
        error_info = f"\n\nErrors ({len(result.errors)}):\n" + "\n".join(
            f"- {err}" for err in result.errors[:5]
        )
        if len(result.errors) > 5:
            error_info += f"\n... and {len(result.errors) - 5} more"

    return (
        f"Reindex complete!\n\n"
        f"Series: {result.series_name}\n"
        f"Episodes processed: {result.episodes_processed}\n"
        f"Documents indexed: {result.documents_indexed}"
        f"{error_info}"
    )


def get_reindex_error_message(error: str) -> str:
    return f"Reindex failed:\n{error}"
```

### 5.10 bot/responses/not_sending_videos/serial_context_handler_responses.py

```python
def get_serial_usage_message() -> str:
    return (
        "Usage: /serial [series_name]\n\n"
        "Show current series or change to a different one.\n"
        "Example: /serial kiepscy"
    )


def get_serial_changed_message(series_name: str) -> str:
    return f"Active series changed to: {series_name}"


def get_serial_invalid_message(series_name: str, available: list) -> str:
    series_list = ", ".join(available) if available else "None"
    return (
        f"Invalid series: {series_name}\n\n"
        f"Available series:\n{series_list}"
    )


def get_serial_current_message(series_name: str) -> str:
    return f"Your current active series: {series_name}"
```

---

## 6. Modyfikacje Istniejących Plików

### 6.1 bot/database/init_db.sql

**Na końcu pliku dodać:**

```sql
-- Multi-serial system: user context
CREATE TABLE IF NOT EXISTS user_series_context (
    user_id BIGINT PRIMARY KEY REFERENCES user_profiles(user_id) ON DELETE CASCADE,
    active_series VARCHAR(50) NOT NULL DEFAULT 'ranczo',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_series_name CHECK (active_series ~ '^[a-z0-9_-]+$')
);

CREATE INDEX IF NOT EXISTS idx_user_series_context_user_id
    ON user_series_context(user_id);
CREATE INDEX IF NOT EXISTS idx_user_series_context_active_series
    ON user_series_context(active_series);

-- Auto-update timestamp
CREATE OR REPLACE FUNCTION update_series_context_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_series_context_timestamp
BEFORE UPDATE ON user_series_context
FOR EACH ROW
EXECUTE FUNCTION update_series_context_timestamp();

-- Auto-create context for new users
CREATE OR REPLACE FUNCTION ensure_user_series_context()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO user_series_context (user_id, active_series)
    VALUES (NEW.user_id, 'ranczo')
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_ensure_user_series_context
AFTER INSERT ON user_profiles
FOR EACH ROW
EXECUTE FUNCTION ensure_user_series_context();

-- Migrate existing users
INSERT INTO user_series_context (user_id, active_series)
SELECT user_id, 'ranczo'
FROM user_profiles
ON CONFLICT (user_id) DO NOTHING;
```

### 6.2 bot/database/database_manager.py

**Dodać metody:**

```python
@staticmethod
async def get_user_active_series(user_id: int) -> str:
    async with DatabaseManager.get_db_connection() as conn:
        result = await conn.fetchval(
            "SELECT active_series FROM user_series_context WHERE user_id = $1",
            user_id
        )
        return result if result else "ranczo"

@staticmethod
async def set_user_active_series(user_id: int, series_name: str) -> None:
    async with DatabaseManager.get_db_connection() as conn:
        await conn.execute(
            """
            INSERT INTO user_series_context (user_id, active_series)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET active_series = $2
            """,
            user_id, series_name
        )
```

### 6.3 bot/database/models.py

**Dodać na końcu:**

```python
@dataclass
class SeriesContext(Serializable):
    user_id: int
    active_series: str
    last_updated: datetime
```

### 6.4 bot/search/transcription_finder.py

**WSZYSTKIE metody statyczne muszą mieć parametr `series_name: str` i filter.**

**Przykład - find_segment_by_quote():**

```python
@staticmethod
async def find_segment_by_quote(
    quote: str,
    logger: logging.Logger,
    series_name: str,  # NEW
    season_filter: Optional[int] = None,
    episode_filter: Optional[int] = None,
    size: int = 1,
) -> Optional[Union[List[ObjectApiResponse], ObjectApiResponse]]:

    index = f"{series_name}_segments"  # MODIFIED

    query = {
        "query": {
            "bool": {
                "must": {
                    "match": {
                        "text": {
                            "query": quote,
                            "fuzziness": "AUTO",
                        },
                    },
                },
                "filter": [
                    # NEW FILTER
                    {"term": {"episode_metadata.series_name": series_name}}
                ],
            },
        },
    }

    if season_filter:
        query["query"]["bool"]["filter"].append(
            {"term": {"episode_metadata.season": season_filter}}
        )

    if episode_filter:
        query["query"]["bool"]["filter"].append(
            {"term": {"episode_metadata.episode_number": episode_filter}}
        )

    hits = (await es.search(index=index, body=query, size=size))["hits"]["hits"]

    # ... rest unchanged
```

**Podobnie dla WSZYSTKICH metod:**
- `find_episodes_by_season()`
- `find_segment_by_id()`
- `get_season_details()`
- etc.

### 6.5 bot/factory/admin_permission_level_factory.py

**Dodać import:**

```python
from bot.handlers.administration.reindex_handler import ReindexHandler
```

**W metodzie `create_handler_classes()` dodać:**

```python
ReindexHandler,
```

### 6.6 bot/factory/subscribed_permission_level_factory.py

**Dodać import:**

```python
from bot.handlers.not_sending_videos.serial_context_handler import SerialContextHandler
```

**W metodzie `create_handler_classes()` dodać:**

```python
SerialContextHandler,
```

### 6.7 bot/handlers/__init__.py

**Dodać eksporty:**

```python
from bot.handlers.administration.reindex_handler import ReindexHandler
from bot.handlers.not_sending_videos.serial_context_handler import SerialContextHandler

__all__ = [
    # ... existing exports
    "ReindexHandler",
    "SerialContextHandler",
]
```

### 6.8 Wszystkie Handlery Używające TranscriptionFinder

**Przykład - bot/handlers/sending_videos/clip_handler.py:**

**Przed:**
```python
segment = await TranscriptionFinder.find_segment_by_quote(
    quote, self._logger
)
```

**Po:**
```python
active_series = self._message.get_state().get("active_series", "ranczo")
segment = await TranscriptionFinder.find_segment_by_quote(
    quote, self._logger, active_series  # NEW
)
```

**Podobnie dla:**
- `bot/handlers/sending_videos/search_handler.py`
- `bot/handlers/sending_videos/manual_clip_handler.py`
- `bot/handlers/sending_videos/select_clip_handler.py`
- `bot/handlers/not_sending_videos/episode_list_handler.py`
- Wszystkie inne używające TranscriptionFinder

### 6.9 bot/platforms/telegram_runner.py

**Dodać middleware w funkcji `run_telegram_bot()`:**

```python
from bot.middlewares.serial_context_middleware import SerialContextMiddleware

async def run_telegram_bot():
    # ... existing code ...

    # Register serial context middleware
    dp.message.middleware(SerialContextMiddleware(logger))

    # ... rest of code ...
```

### 6.10 README.md

**Po sekcji "Kluczowe Komendy" (około linia 46) dodać:**

```markdown
## Multi-Serial Support

RanchBot supports multiple TV series with user-specific context:

### User Commands
- **`/serial [nazwa]`**: Switch your active series (default: ranczo)
- All search commands (`/klip`, `/szukaj`, etc.) work within your active series context

### Admin Commands
- **`/reindex all`**: Reindex all series from zip archives
- **`/reindex all-new`**: Reindex only series without Elasticsearch indices
- **`/reindex [series_name]`**: Reindex specific series (overwrites existing data)

### Architecture
- **7 Elasticsearch indices per series**: segments, text_embeddings, video_frames, episode_names, full_episode_embeddings, sound_events, sound_event_embeddings
- **Real-time zip extraction**: Archives are processed in-memory, no disk writes
- **Video path transformation**: Automatically updates paths from old structure to new
- **Backward compatibility**: Existing commands work without changes
```

### 6.11 COMMANDS.md

**Po sekcji "Komendy Administracyjne" (około linia 68) dodać:**

```markdown
## Multi-Serial Commands

### For All Users
- **`/serial`** / **`/ser`**: 📺 Show your current active series
- **`/serial [nazwa]`** / **`/ser [nazwa]`**: 📺 Change your active series. All search commands will use this context. Example: `/serial kiepscy`

### For Admins Only
- **`/reindex all`**: 🔄 Reindex all TV series from zip archives. This recreates all Elasticsearch indices.
- **`/reindex all-new`**: 🔄 Reindex only series that don't have Elasticsearch indices yet.
- **`/reindex [series_name]`**: 🔄 Reindex specific series. Example: `/reindex ranczo`

**Note**: Reindexing processes zip files from `preprocessor/output_data/archives/` and updates video paths to `preprocessor/output_data/transcoded_videos/`.

---
```

### 6.12 bot/handlers/not_sending_videos/start_handler.py

**W metodzie `_do_handle()`, w help message dodać:**

```python
"📺 /serial [nazwa] - Change active series\n"
"(Admin) 🔄 /reindex [target] - Reindex data\n"
```

---

## 7. Testy

### 7.1 test/test_database_series_context.py

```python
import pytest
from bot.database.database_manager import DatabaseManager


@pytest.mark.asyncio
async def test_get_user_active_series_default():
    user_id = 999999
    series = await DatabaseManager.get_user_active_series(user_id)
    assert series == "ranczo"


@pytest.mark.asyncio
async def test_set_and_get_user_active_series():
    user_id = 999999
    await DatabaseManager.set_user_active_series(user_id, "kiepscy")
    series = await DatabaseManager.get_user_active_series(user_id)
    assert series == "kiepscy"


@pytest.mark.asyncio
async def test_update_existing_series_context():
    user_id = 999999
    await DatabaseManager.set_user_active_series(user_id, "ranczo")
    await DatabaseManager.set_user_active_series(user_id, "alternatywy4")
    series = await DatabaseManager.get_user_active_series(user_id)
    assert series == "alternatywy4"


@pytest.mark.asyncio
async def test_trigger_auto_create_context():
    user_id = 888888

    from bot.database.models import UserProfile
    profile = UserProfile(
        user_id=user_id,
        username="testuser",
        full_name="Test User"
    )
    await DatabaseManager.add_user_to_database(profile)

    series = await DatabaseManager.get_user_active_series(user_id)
    assert series == "ranczo"
```

### 7.2 test/test_zip_extractor.py

```python
import pytest
from pathlib import Path
from bot.services.reindex.zip_extractor import ZipExtractor
import logging


@pytest.fixture
def logger():
    return logging.getLogger("test")


@pytest.fixture
def sample_zip():
    return Path("preprocessor/output_data/archives/S00/E01/ranczo_S00E01_elastic_documents.zip")


def test_extract_zip_to_memory(logger, sample_zip):
    if not sample_zip.exists():
        pytest.skip("Sample zip not found")

    extractor = ZipExtractor(logger)
    files = extractor.extract_to_memory(sample_zip)

    assert "text_segments" in files
    assert "text_embeddings" in files
    assert "video_frames" in files
    assert "episode_names" in files


def test_parse_jsonl_from_memory(logger, sample_zip):
    if not sample_zip.exists():
        pytest.skip("Sample zip not found")

    extractor = ZipExtractor(logger)
    files = extractor.extract_to_memory(sample_zip)

    documents = extractor.parse_jsonl_from_memory(files["text_segments"])

    assert len(documents) > 0
    assert "episode_id" in documents[0]
    assert "text" in documents[0]
    assert "video_path" in documents[0]


def test_corrupted_zip(logger, tmp_path):
    corrupted_zip = tmp_path / "corrupted.zip"
    corrupted_zip.write_text("not a zip file")

    extractor = ZipExtractor(logger)

    with pytest.raises(ValueError, match="Invalid zip file"):
        extractor.extract_to_memory(corrupted_zip)
```

### 7.3 test/test_series_scanner.py

```python
import pytest
from bot.services.reindex.series_scanner import SeriesScanner
import logging


@pytest.fixture
def logger():
    return logging.getLogger("test")


def test_scan_all_series(logger):
    scanner = SeriesScanner(logger)
    series = scanner.scan_all_series()

    assert isinstance(series, list)
    if series:
        assert "ranczo" in series


def test_detect_series_from_filename(logger):
    scanner = SeriesScanner(logger)

    filename = "ranczo_S01E01_elastic_documents.zip"
    series = scanner._detect_series_from_filename(filename)
    assert series == "ranczo"

    filename2 = "kiepscy_S02E05_elastic_documents.zip"
    series2 = scanner._detect_series_from_filename(filename2)
    assert series2 == "kiepscy"


def test_extract_episode_code(logger):
    scanner = SeriesScanner(logger)

    filename = "ranczo_S01E01.mp4"
    code = scanner._extract_episode_code(filename)
    assert code == "S01E01"

    filename2 = "kiepscy_S10E13.mp4"
    code2 = scanner._extract_episode_code(filename2)
    assert code2 == "S10E13"


def test_scan_series_zips(logger):
    scanner = SeriesScanner(logger)
    zips = scanner.scan_series_zips("ranczo")

    assert isinstance(zips, list)
    if zips:
        assert all("ranczo" in str(z).lower() for z in zips)


def test_scan_series_mp4s(logger):
    scanner = SeriesScanner(logger)
    mp4s = scanner.scan_series_mp4s("ranczo")

    assert isinstance(mp4s, dict)
    if mp4s:
        episode_codes = list(mp4s.keys())
        assert all(code.startswith("S") for code in episode_codes)
```

### 7.4 test/test_reindex_service.py

```python
import pytest
from bot.services.reindex.reindex_service import ReindexService
import logging


@pytest.fixture
def logger():
    return logging.getLogger("test")


@pytest.mark.asyncio
async def test_reindex_single_series(logger):
    service = ReindexService(logger)

    progress_messages = []

    async def progress_callback(msg, cur, tot):
        progress_messages.append(msg)

    result = await service.reindex_series("ranczo", progress_callback)

    assert result.series_name == "ranczo"
    assert result.episodes_processed > 0
    assert result.documents_indexed > 0
    assert len(progress_messages) > 0


@pytest.mark.asyncio
async def test_reindex_invalid_series(logger):
    service = ReindexService(logger)

    async def progress_callback(msg, cur, tot):
        pass

    with pytest.raises(ValueError, match="No zip files found"):
        await service.reindex_series("nonexistent_series", progress_callback)


@pytest.mark.asyncio
async def test_reindex_all_new(logger):
    service = ReindexService(logger)

    async def progress_callback(msg, cur, tot):
        pass

    results = await service.reindex_all_new(progress_callback)

    assert isinstance(results, list)
```

### 7.5 test/test_serial_context_handler.py

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.handlers.not_sending_videos.serial_context_handler import SerialContextHandler


@pytest.mark.asyncio
async def test_show_current_series():
    message = MagicMock()
    message.get_text.return_value = "/serial"
    message.get_user_id.return_value = 123

    responder = AsyncMock()
    logger = MagicMock()

    handler = SerialContextHandler(message, responder, logger)
    handler.serial_manager.get_user_active_series = AsyncMock(return_value="ranczo")

    await handler._do_handle()

    responder.send_text.assert_called_once()
    call_args = responder.send_text.call_args[0][0]
    assert "ranczo" in call_args.lower()


@pytest.mark.asyncio
async def test_change_series_valid():
    message = MagicMock()
    message.get_text.return_value = "/serial kiepscy"
    message.get_user_id.return_value = 123

    responder = AsyncMock()
    logger = MagicMock()

    handler = SerialContextHandler(message, responder, logger)
    handler.serial_manager.list_available_series = AsyncMock(return_value=["ranczo", "kiepscy"])
    handler.serial_manager.set_user_active_series = AsyncMock()

    await handler._do_handle()

    handler.serial_manager.set_user_active_series.assert_called_once_with(123, "kiepscy")


@pytest.mark.asyncio
async def test_change_series_invalid():
    message = MagicMock()
    message.get_text.return_value = "/serial nonexistent"
    message.get_user_id.return_value = 123

    responder = AsyncMock()
    logger = MagicMock()

    handler = SerialContextHandler(message, responder, logger)
    handler.serial_manager.list_available_series = AsyncMock(return_value=["ranczo"])

    await handler._do_handle()

    responder.send_text.assert_called_once()
    call_args = responder.send_text.call_args[0][0]
    assert "invalid" in call_args.lower() or "available" in call_args.lower()
```

---

## 8. Dokumentacja

### 8.1 README.md - Multi-Serial Section (wstawić po linii 46)

```markdown
## Multi-Serial Support

RanchBot supports multiple TV series with user-specific context:

### User Commands
- **`/serial [nazwa]`**: Switch your active series (default: ranczo)
  - View current series: `/serial`
  - Change series: `/serial kiepscy`
- All search commands (`/klip`, `/szukaj`, `/kompiluj`, etc.) automatically work within your active series context
- Each user has their own independent serial context

### Admin Commands
- **`/reindex all`**: Reindex all series from zip archives
  - Scans `preprocessor/output_data/archives/` for all series
  - Deletes and recreates all Elasticsearch indices
  - Updates video paths to new structure
- **`/reindex all-new`**: Reindex only series without Elasticsearch indices
  - Useful for adding new series without re-processing existing ones
- **`/reindex [series_name]`**: Reindex specific series
  - Example: `/reindex ranczo`
  - Overwrites existing data for that series

### Architecture
- **7 Elasticsearch indices per series**:
  - `{series}_segments` - dialogue segments (BM25 full-text search)
  - `{series}_text_embeddings` - semantic text search (4096D vectors)
  - `{series}_video_frames` - visual search + character/object detection
  - `{series}_episode_names` - episode title search
  - `{series}_full_episode_embeddings` - whole-episode embeddings
  - `{series}_sound_events` - audio event search
  - `{series}_sound_event_embeddings` - semantic audio search
- **Real-time zip extraction**: Archives processed in-memory (BytesIO), no disk writes
- **Video path transformation**: Automatically updates paths from old structure to new
- **Backward compatibility**: Existing commands work without changes, default context is "ranczo"
- **PostgreSQL context table**: `user_series_context` stores each user's active series

### Data Structure
```
preprocessor/output_data/
  archives/{SEASON}/{EPISODE}/{series}_{CODE}_elastic_documents.zip
  transcoded_videos/{SEASON}/{series}_{CODE}.mp4

Example:
  archives/S01/E01/ranczo_S01E01_elastic_documents.zip
  transcoded_videos/S01/ranczo_S01E01.mp4
```
```

### 8.2 COMMANDS.md - Multi-Serial Section (wstawić po linii 68)

```markdown
## 📺 Multi-Serial Commands

### For All Users

- **`/serial`** / **`/ser`**: 📺 Show your current active series
  - Example: `/serial` → "Your current active series: ranczo"

- **`/serial [nazwa]`** / **`/ser [nazwa]`**: 📺 Change your active series
  - All search commands will use this context
  - Example: `/serial kiepscy` → "Active series changed to: kiepscy"
  - After changing, `/klip` will search in "kiepscy", not "ranczo"

### For Admins Only

- **`/reindex all`**: 🔄 Reindex all TV series from zip archives
  - Scans all zips in `preprocessor/output_data/archives/`
  - Recreates all Elasticsearch indices for all series
  - Updates video paths to new structure
  - Progress reporting during process
  - Example: `/reindex all`

- **`/reindex all-new`**: 🔄 Reindex only series without Elasticsearch indices
  - Checks which series already have indices
  - Only processes series without existing indices
  - Useful for adding new series without re-processing old ones
  - Example: `/reindex all-new`

- **`/reindex [series_name]`**: 🔄 Reindex specific series
  - Deletes existing indices for that series
  - Recreates indices from zip archives
  - Updates video paths
  - Example: `/reindex ranczo` → Reindex only "ranczo" series

**Technical Details**:
- Reindexing processes zip files from `preprocessor/output_data/archives/`
- Video paths updated to `preprocessor/output_data/transcoded_videos/`
- Zips are extracted in-memory (realtime), not written to disk
- Each series has 7 Elasticsearch indices (segments, embeddings, frames, etc.)
- Process is logged and errors are reported

---
```

### 8.3 API Documentation - OpenAPI Schema Addition

**Plik:** `api_doc.md` lub schema w `rest_runner.py`

```yaml
/api/v1/serial:
  post:
    summary: Change user's active series context
    description: |
      Sets the active series for the authenticated user. All subsequent search
      commands will filter results within this series context.
    tags:
      - Commands
      - Multi-Serial
    security:
      - bearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              args:
                type: array
                items:
                  type: string
                minItems: 0
                maxItems: 1
                description: |
                  Empty array to get current series.
                  Array with one string to change series.
                example: ["ranczo"]
              reply_json:
                type: boolean
                default: false
    responses:
      200:
        description: Series context updated or retrieved
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Active series changed to: ranczo"
      401:
        description: Unauthorized - invalid or missing token
      400:
        description: Bad request - invalid series name

/api/v1/reindex:
  post:
    summary: Reindex series from zip archives (Admin only)
    description: |
      Triggers reindexing of TV series data from zip archives to Elasticsearch.
      Supports reindexing all series, only new series, or a specific series.

      **Admin permission required.**

      Process:
      1. Scans preprocessor/output_data/archives/ for zips
      2. Deletes existing indices (if any)
      3. Extracts zips to memory (realtime)
      4. Updates video_path in documents
      5. Bulk indexes to Elasticsearch
      6. Reports progress and results
    tags:
      - Commands
      - Admin
      - Multi-Serial
    security:
      - bearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              args:
                type: array
                items:
                  type: string
                minItems: 1
                maxItems: 1
                description: |
                  Target for reindexing:
                  - "all": reindex all series
                  - "all-new": reindex only series without indices
                  - "{series_name}": reindex specific series (e.g. "ranczo")
                example: ["all"]
              reply_json:
                type: boolean
                default: false
    responses:
      200:
        description: Reindex operation completed
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: |
                    Reindex complete! Series: ranczo, Episodes: 130, Documents: 45000
                progress_messages:
                  type: array
                  items:
                    type: string
      401:
        description: Unauthorized - invalid or missing token
      403:
        description: Forbidden - admin permission required
      400:
        description: Bad request - invalid target
      500:
        description: Internal error during reindexing
```

---

## 9. Sekwencja Implementacji

### Krok 1: Database Schema (1-2h)

**Cele:**
- Dodać tabele do bazy danych
- Utworzyć model dataclass
- Dodać metody do DatabaseManager
- Uruchomić migrację
- Przetestować

**Pliki:**
1. `bot/database/init_db.sql` - dodać SQL (sekcja 4.1-4.4)
2. `bot/database/models.py` - dodać SeriesContext (sekcja 4.5)
3. `bot/database/database_manager.py` - dodać metody (sekcja 6.2)

**Test:**
```bash
pytest test/test_database_series_context.py -v
```

**Checkpoint:**
- [ ] Tabela `user_series_context` istnieje w DB
- [ ] Triggery działają (auto-create, auto-update timestamp)
- [ ] Metody get/set active_series działają
- [ ] Istniejący użytkownicy zmigrowani

---

### Krok 2: Serial Context Infrastructure (2-3h)

**Cele:**
- Utworzyć SerialContextManager
- Utworzyć SerialContextMiddleware
- Utworzyć SerialContextHandler
- Zarejestrować handler w factory
- Zarejestrować middleware w dispatcher

**Pliki:**
1. `bot/services/serial_context/serial_context_manager.py` (sekcja 5.8)
2. `bot/middlewares/serial_context_middleware.py` (sekcja 5.3)
3. `bot/handlers/not_sending_videos/serial_context_handler.py` (sekcja 5.2)
4. `bot/responses/not_sending_videos/serial_context_handler_responses.py` (sekcja 5.10)
5. `bot/factory/subscribed_permission_level_factory.py` (sekcja 6.6)
6. `bot/handlers/__init__.py` (sekcja 6.7)
7. `bot/platforms/telegram_runner.py` (sekcja 6.9)

**Test:**
```bash
pytest test/test_serial_context_handler.py -v
```

**Manual Test (Telegram):**
```
/serial              → "Your current active series: ranczo"
/serial kiepscy      → "Active series changed to: kiepscy"
/serial nonexistent  → Error message
```

**Checkpoint:**
- [ ] Middleware wstrzykuje `active_series` do state
- [ ] `/serial` pokazuje obecny serial
- [ ] `/serial [nazwa]` zmienia serial
- [ ] Walidacja nazwy serialu działa
- [ ] Logi pokazują zmiany kontekstu

---

### Krok 3: Reindex Services Foundation (3-4h)

**Cele:**
- Utworzyć SeriesScanner
- Utworzyć ZipExtractor
- Utworzyć VideoPathTransformer
- Przetestować każdy moduł

**Pliki:**
1. `bot/services/reindex/series_scanner.py` (sekcja 5.7)
2. `bot/services/reindex/zip_extractor.py` (sekcja 5.5)
3. `bot/services/reindex/video_path_transformer.py` (sekcja 5.6)

**Test:**
```bash
pytest test/test_series_scanner.py -v
pytest test/test_zip_extractor.py -v
```

**Checkpoint:**
- [ ] SeriesScanner znajduje wszystkie seriale
- [ ] SeriesScanner wykrywa nazwę serialu z filename
- [ ] SeriesScanner mapuje zipy na mp4
- [ ] ZipExtractor rozpakowuje do BytesIO
- [ ] ZipExtractor parsuje JSONL
- [ ] ZipExtractor obsługuje corrupted zipy
- [ ] VideoPathTransformer aktualizuje ścieżki
- [ ] VideoPathTransformer waliduje istnienie plików

---

### Krok 4: Reindex Service Integration (4-5h)

**Cele:**
- Utworzyć ReindexService
- Zintegrować wszystkie komponenty
- Dodać progress tracking
- Przetestować na małym zbiorze danych

**Pliki:**
1. `bot/services/reindex/reindex_service.py` (sekcja 5.4)

**Test:**
```bash
pytest test/test_reindex_service.py -v
```

**Manual Test (Python REPL):**
```python
import asyncio
import logging
from bot.services.reindex.reindex_service import ReindexService

logger = logging.getLogger()
service = ReindexService(logger)

async def progress(msg, cur, tot):
    print(f"{msg} ({cur}/{tot})")

asyncio.run(service.reindex_series("ranczo", progress))
```

**Checkpoint:**
- [ ] reindex_series() działa end-to-end
- [ ] reindex_all() przetwarza wszystkie seriale
- [ ] reindex_all_new() pomija istniejące
- [ ] Progress callback wywołany co ~2s
- [ ] Błędy nie crashują procesu
- [ ] Logi pokazują postęp
- [ ] Elasticsearch indices utworzone

---

### Krok 5: Reindex Handler (2h)

**Cele:**
- Utworzyć ReindexHandler
- Dodać response messages
- Zarejestrować w admin factory
- Przetestować przez Telegram

**Pliki:**
1. `bot/handlers/administration/reindex_handler.py` (sekcja 5.1)
2. `bot/responses/administration/reindex_handler_responses.py` (sekcja 5.9)
3. `bot/factory/admin_permission_level_factory.py` (sekcja 6.5)
4. `bot/handlers/__init__.py` (sekcja 6.7)

**Test:**
```bash
pytest test/test_reindex_handler.py -v
```

**Manual Test (Telegram - as admin):**
```
/reindex                → Usage message
/reindex all            → Reindex all series
/reindex all-new        → Reindex only new
/reindex ranczo         → Reindex ranczo
/reindex nonexistent    → Error (no zips found)
```

**Checkpoint:**
- [ ] Komenda `/reindex` dostępna dla adminów
- [ ] Walidacja argumentów działa
- [ ] Progress messages wyświetlane
- [ ] Błędy raportowane użytkownikowi
- [ ] Sukces raportowany z podsumowaniem
- [ ] Logi zawierają szczegóły

---

### Krok 6: Modify Existing Handlers (3-4h)

**Cele:**
- Zmodyfikować TranscriptionFinder (dodać parametr series_name)
- Zaktualizować wszystkie handlery używające TranscriptionFinder
- Dodać filtrowanie po series_name w queries

**Pliki:**
1. `bot/search/transcription_finder.py` (sekcja 6.4)
2. `bot/handlers/sending_videos/clip_handler.py` (sekcja 6.8)
3. `bot/handlers/sending_videos/search_handler.py`
4. `bot/handlers/sending_videos/manual_clip_handler.py`
5. `bot/handlers/sending_videos/select_clip_handler.py`
6. `bot/handlers/not_sending_videos/episode_list_handler.py`
7. Wszystkie inne handlery używające TranscriptionFinder

**Test:**
```bash
pytest test/test_transcription_finder.py -v
pytest test/test_clip_handler_with_series.py -v
```

**Manual Test (Telegram):**
```
/serial ranczo
/klip cytat      → Zwraca wynik z ranczo

/serial kiepscy
/klip cytat      → Zwraca wynik z kiepscy (lub brak wyników jeśli nie ma)
```

**Checkpoint:**
- [ ] TranscriptionFinder ma parametr `series_name` we wszystkich metodach
- [ ] Queries filtrują po `episode_metadata.series_name`
- [ ] Index name to `f"{series_name}_{index_type}"`
- [ ] Wszystkie handlery przekazują `active_series`
- [ ] Backward compatibility (domyślnie "ranczo")
- [ ] Wyszukiwania działają per serial

---

### Krok 7: REST API Integration (2h)

**Cele:**
- Dodać endpoint `/api/v1/serial`
- Dodać endpoint `/api/v1/reindex`
- Zaktualizować OpenAPI docs
- Przetestować przez curl/Postman

**Pliki:**
1. `bot/platforms/rest_runner.py` - dodać endpointy (jeśli nie są automatycznie mapowane)
2. `api_doc.md` - dodać dokumentację (sekcja 8.3)

**Test:**
```bash
# Get current series
curl -X POST http://localhost:8000/api/v1/serial \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"args": []}'

# Change series
curl -X POST http://localhost:8000/api/v1/serial \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"args": ["kiepscy"]}'

# Reindex (as admin)
curl -X POST http://localhost:8000/api/v1/reindex \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"args": ["all-new"]}'
```

**Checkpoint:**
- [ ] `/api/v1/serial` działa (GET current / POST change)
- [ ] `/api/v1/reindex` działa (admin only)
- [ ] Autoryzacja sprawdzana
- [ ] Błędy zwracają proper HTTP status codes
- [ ] Response JSON czytelny
- [ ] OpenAPI docs zaktualizowane

---

### Krok 8: Documentation (1h)

**Cele:**
- Zaktualizować README.md
- Zaktualizować COMMANDS.md
- Zaktualizować help message w start_handler

**Pliki:**
1. `README.md` (sekcja 6.10)
2. `COMMANDS.md` (sekcja 6.11)
3. `bot/handlers/not_sending_videos/start_handler.py` (sekcja 6.12)

**Manual Test:**
```
/start   → Help message zawiera /serial i /reindex
```

**Checkpoint:**
- [ ] README.md ma sekcję "Multi-Serial Support"
- [ ] COMMANDS.md ma sekcję "Multi-Serial Commands"
- [ ] Help message pokazuje nowe komendy
- [ ] Dokumentacja jasna i kompletna
- [ ] Przykłady działają

---

### Krok 9: Integration Testing (2-3h)

**Cele:**
- Przetestować pełny flow end-to-end
- Przetestować edge cases
- Sprawdzić performance
- Naprawić znalezione bugi

**Scenariusze testowe:**

1. **Full Reindex Flow:**
   ```
   /reindex all
   → Verify all indices created in Elasticsearch
   → Verify video_path updated
   → Verify all documents indexed
   ```

2. **Serial Context Flow:**
   ```
   User A: /serial ranczo
   User A: /klip cytat   → wynik z ranczo

   User B: /serial kiepscy
   User B: /klip cytat   → wynik z kiepscy (nie ranczo!)

   User A: /klip cytat   → wciąż ranczo (kontekst per user)
   ```

3. **Edge Cases:**
   ```
   /reindex nonexistent   → Error message
   /serial nonexistent    → Error message
   /klip w pustym serialu → No results
   Corrupted zip          → Skip with log, continue
   Missing MP4            → Warning log, keep old path
   ```

4. **Performance:**
   ```
   /reindex all z 130 odcinkami
   → Czas < 5 minut
   → Progress messages co 2s
   → Memory usage stabilna
   ```

**Checkpoint:**
- [ ] Wszystkie scenariusze działają
- [ ] Edge cases obsłużone
- [ ] Performance akceptowalna
- [ ] Brak memory leaks
- [ ] Logi czytelne i pomocne

---

### Krok 10: Performance & Cleanup (1-2h)

**Cele:**
- Sprawdzić performance reindexowania
- Dodać logi do kluczowych miejsc
- Code review
- Cleanup zbędnych komentarzy/debugów

**Zadania:**

1. **Performance Check:**
   - Zmierzyć czas reindex dla 1 odcinka
   - Zmierzyć czas reindex dla całego serialu
   - Sprawdzić memory usage podczas reindex
   - Sprawdzić czy async operations są efektywne

2. **Logging:**
   - Verify logi na poziomie INFO dla ważnych eventów
   - Verify logi na poziomie DEBUG dla szczegółów
   - Verify logi na poziomie ERROR dla błędów
   - Remove debug prints

3. **Code Review:**
   - Check SOLID principles
   - Check DRY (no duplication)
   - Check naming conventions
   - Check error handling
   - Check async/await usage

4. **Cleanup:**
   - Remove commented code
   - Remove debug prints
   - Remove TODO comments
   - Fix linter warnings
   - Format code consistently

**Checkpoint:**
- [ ] Performance measurements recorded
- [ ] Logi kompletne i właściwe
- [ ] Code review passed
- [ ] No linter warnings
- [ ] Code formatted
- [ ] Ready for production

---

**TOTAL ESTIMATED TIME: 23-30 hours**

---

## 10. Weryfikacja

### 10.1 Checklist Pre-Deployment

**Database:**
- [ ] Tabela `user_series_context` istnieje
- [ ] Triggery działają
- [ ] Migracja istniejących użytkowników wykonana
- [ ] Indeksy utworzone

**Backend:**
- [ ] Wszystkie nowe moduły utworzone
- [ ] Wszystkie istniejące pliki zmodyfikowane
- [ ] Wszystkie testy przechodzą
- [ ] Linter nie pokazuje błędów

**Functionality:**
- [ ] `/serial` działa
- [ ] `/reindex` działa (all, all-new, series_name)
- [ ] Middleware wstrzykuje kontekst
- [ ] TranscriptionFinder filtruje po serialu
- [ ] Wszystkie handlery używają kontekstu

**REST API:**
- [ ] `/api/v1/serial` działa
- [ ] `/api/v1/reindex` działa
- [ ] Autoryzacja sprawdzana

**Documentation:**
- [ ] README.md zaktualizowany
- [ ] COMMANDS.md zaktualizowany
- [ ] Help message zaktualizowany
- [ ] API docs zaktualizowane

**Testing:**
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual tests wykonane
- [ ] Edge cases przetestowane

### 10.2 Post-Deployment Verification

**Po wdrożeniu na produkcję:**

1. **Database Check:**
   ```sql
   SELECT COUNT(*) FROM user_series_context;
   SELECT active_series, COUNT(*) FROM user_series_context GROUP BY active_series;
   ```

2. **Elasticsearch Check:**
   ```bash
   curl http://localhost:9200/_cat/indices?v | grep ranczo
   curl http://localhost:9200/_cat/indices?v | grep kiepscy
   ```

3. **Test Reindex:**
   ```
   /reindex all-new    → Should process new series (or report none)
   ```

4. **Test User Flow:**
   ```
   /serial             → "Your current active series: ranczo"
   /serial kiepscy     → "Active series changed to: kiepscy"
   /klip test          → Results from kiepscy
   /serial ranczo      → "Active series changed to: ranczo"
   /klip test          → Results from ranczo
   ```

5. **Monitor Logs:**
   - Check for errors
   - Check for warnings
   - Verify INFO logs show operations

6. **Performance Check:**
   - Response times normal
   - Memory usage stable
   - No crashes

### 10.3 Rollback Plan

**Jeśli coś pójdzie nie tak:**

1. **Database Rollback:**
   ```sql
   DROP TABLE IF EXISTS user_series_context CASCADE;
   DROP TRIGGER IF EXISTS trigger_ensure_user_series_context ON user_profiles;
   DROP TRIGGER IF EXISTS trigger_update_series_context_timestamp ON user_series_context;
   DROP FUNCTION IF EXISTS ensure_user_series_context();
   DROP FUNCTION IF EXISTS update_series_context_timestamp();
   ```

2. **Code Rollback:**
   ```bash
   git revert [commit_hash]
   git push
   ```

3. **Elasticsearch Rollback:**
   - Stare indeksy (bez prefiksu serial) powinny wciąż istnieć
   - Jeśli usunięte, trzeba reindexować ze starych danych

4. **Communication:**
   - Poinformować użytkowników o problemie
   - Podać ETA naprawy
   - Rollback do poprzedniej wersji

---

## Podsumowanie

Ten dokument zawiera **KOMPLETNY plan implementacji** systemu multi-serialowego z reindexowaniem z zipów dla RanchBot.

**Zawiera:**
- ✅ Pełny kontekst i wymagania
- ✅ Wyniki eksploracji kodu (3 agenty)
- ✅ Architekturę z diagramami ASCII
- ✅ Schemat bazy danych (SQL + triggery)
- ✅ Pełny kod wszystkich nowych modułów
- ✅ Szczegółowe modyfikacje istniejących plików
- ✅ Kompletne testy
- ✅ Aktualizacje dokumentacji
- ✅ Sekwencję implementacji krok po kroku (10 kroków, 23-30h)
- ✅ Checklisty weryfikacji
- ✅ Plan rollbacku

**Klucz do sukcesu:**
1. Następuj sekwencji implementacji
2. Testuj każdy krok przed przejściem dalej
3. Używaj checklistów do weryfikacji
4. Commituj po każdym ukończonym kroku
5. Dokumentuj napotykane problemy

**Gotowe do implementacji jutro!** 🚀

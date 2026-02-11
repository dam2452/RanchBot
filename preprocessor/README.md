# Video Preprocessing Pipeline

Docker pipeline do przetwarzania wideo z GPU: transkodowanie, transkrypcja, detekcja scen, rozpoznawanie postaci, embeddingi → Elasticsearch.

**Wymagania:** GPU z CUDA (RTX 3090 24GB zalecane) • NVIDIA Container Toolkit • Docker Compose

---

## Quick Start

```bash
cd preprocessor
mkdir -p input_data output_data
docker compose build

# Podstawowe użycie - pełny pipeline
./run-preprocessor.sh run-all --series ranczo

# Z pomijaniem konkretnych kroków
./run-preprocessor.sh run-all --series kiepscy --skip transcode --skip transcribe

# Wymuszenie ponownego przetworzenia (ignoruje cache)
./run-preprocessor.sh run-all --series ranczo --force-rerun

# Pojedynczy krok
./run-preprocessor.sh transcode --series ranczo
./run-preprocessor.sh detect-scenes --series ranczo

# Search
./run-preprocessor.sh search --series ranczo --text "Lucy Wilska"
./run-preprocessor.sh search --series kiepscy --stats
```

**Konfiguracja:** Wszystkie parametry (URLs do scrapingu, tryby transkrypcji, bitrate, etc.) są w plikach `series_configs/*.json`

---

## Konfiguracja per-seria

Pipeline używa plików JSON w `series_configs/` do konfiguracji każdego serialu:

**Struktura:**
```
series_configs/
├── defaults.json          # Domyślne ustawienia dla wszystkich seriali
├── ranczo.json           # Nadpisuje defaults tylko dla Ranczo
└── kiepscy.json          # Nadpisuje defaults tylko dla Kiepskich
```

**Przykład `kiepscy.json`:**
```json
{
  "display_name": "Świat według Kiepskich",
  "series_name": "kiepscy",
  "pipeline_mode": "full",
  "indexing": {
    "elasticsearch": {
      "index_name": "kiepscy_clips"
    }
  },
  "processing": {
    "transcode": {
      "force_deinterlace": true,
      "video_bitrate_mbps": 2.5
    },
    "transcription": {
      "mode": "whisper",
      "model": "large-v3-turbo"
    }
  },
  "scraping": {
    "episodes": {
      "parser_mode": "premium",
      "urls": ["https://pl.wikipedia.org/wiki/Lista_odcinków..."]
    },
    "characters": {
      "parser_mode": "premium",
      "urls": ["https://pl.wikipedia.org/wiki/Lista_postaci..."]
    },
    "character_references": {
      "search_engine": "google"
    }
  },
  "skip_steps": []
}
```

**Tryby pipeline:**
- `"pipeline_mode": "full"` - uruchamia wszystkie kroki
- `"pipeline_mode": "selective"` - pomija kroki z `skip_steps` automatycznie

**Dostępne parametry:** Zobacz `defaults.json` dla pełnej listy opcji konfiguracyjnych.

---

## Pipeline (20 kroków)

```
SCRAPING                  PROCESSING                              INDEXING                 VALIDATION
──────────────────────────────────────────────────────────────────────────────────────────────────────
[1] scrape_episodes  ──┬─→ [4] transcode ─→ [5] transcribe ─→ [6] separate_sounds
[2] scrape_characters  │   [7] analyze_text                                        ────┐
[3] process_references─┘   [8] detect_scenes ─→ [9] export_frames                     │
                           [10] text_embeddings                                         │
                           [11] video_embeddings                                        ├─→ [20] validate
                           [12] image_hashing                                           │
                           [13] detect_characters                                       │
                           [14] detect_emotions                                         │
                           [15] cluster_faces                                           │
                           [16] detect_objects                                          │
                           [17] generate_elastic_docs ─→ [18] generate_archives ─→ [19] index_to_elasticsearch ─┘
```

**Kroki są automatycznie wykonywane w poprawnej kolejności** - pipeline rozwiązuje zależności i tworzy plan wykonania.

**Validation (krok 20)** - uruchamiany na końcu, weryfikuje poprawność wszystkich poprzednich kroków pipeline.

---

## Dostępne komendy

```bash
# Pipeline
./run-preprocessor.sh run-all --series NAZWA [--skip STEP_ID ...] [--force-rerun]

# Scraping
./run-preprocessor.sh scrape-episodes --series NAZWA
./run-preprocessor.sh scrape-characters --series NAZWA
./run-preprocessor.sh process-references --series NAZWA

# Video processing
./run-preprocessor.sh transcode --series NAZWA
./run-preprocessor.sh detect-scenes --series NAZWA
./run-preprocessor.sh export-frames --series NAZWA

# Audio/Text processing
./run-preprocessor.sh transcribe --series NAZWA
./run-preprocessor.sh separate-sounds --series NAZWA
./run-preprocessor.sh analyze-text --series NAZWA

# Embeddings
./run-preprocessor.sh text-embeddings --series NAZWA
./run-preprocessor.sh video-embeddings --series NAZWA

# Visual analysis
./run-preprocessor.sh image-hashing --series NAZWA
./run-preprocessor.sh detect-characters --series NAZWA
./run-preprocessor.sh detect-emotions --series NAZWA
./run-preprocessor.sh cluster-faces --series NAZWA
./run-preprocessor.sh detect-objects --series NAZWA

# Indexing
./run-preprocessor.sh generate-elastic-docs --series NAZWA
./run-preprocessor.sh generate-archives --series NAZWA
./run-preprocessor.sh index-to-elasticsearch --series NAZWA

# Validation
./run-preprocessor.sh validate --series NAZWA

# Search (wymaga uruchomionego Elasticsearch)
./run-preprocessor.sh search --series NAZWA --text "query"
./run-preprocessor.sh search --series NAZWA --text-semantic "query"
./run-preprocessor.sh search --series NAZWA --image /input_data/screenshot.jpg
./run-preprocessor.sh search --series NAZWA --character "Postać"
./run-preprocessor.sh search --series NAZWA --emotion "happiness"
./run-preprocessor.sh search --series NAZWA --object "person:5+"
./run-preprocessor.sh search --series NAZWA --stats
./run-preprocessor.sh search --series NAZWA --list-characters

# Utilities
./run-preprocessor.sh visualize --series NAZWA  # Wizualizacja grafu zależności
./run-preprocessor.sh bash                       # Shell w kontenerze
```

**Parametry:**
- `--series NAZWA` - **WYMAGANY** dla wszystkich komend (np. `ranczo`, `kiepscy`)
- `--force-rerun` - Ignoruje cache i przetwarza ponownie
- `--skip STEP_ID` - Pomija konkretny krok (można użyć wielokrotnie)

**Step IDs do --skip:**
```
scrape_episodes, scrape_characters, process_references,
transcode, transcribe, separate_sounds, analyze_text,
detect_scenes, export_frames, text_embeddings, video_embeddings,
image_hashing, detect_characters, detect_emotions, cluster_faces, detect_objects,
generate_elastic_docs, generate_archives, index_to_elasticsearch,
validate
```

---

## Multi-Series Support

Pipeline wspiera przetwarzanie wielu seriali jednocześnie. Każdy serial ma dedykowany folder i konfigurację.

**Input struktura:**
```
input_data/
├── ranczo/
│   ├── S01/
│   │   ├── S01E01.mp4
│   │   └── S01E02.mp4
│   ├── S02/
│   └── S03/
└── kiepscy/
    ├── S01/
    └── S02/
```

**Output struktura:**
```
output_data/
├── ranczo/
│   ├── transcoded_videos/
│   ├── transcriptions/
│   ├── scene_timestamps/
│   ├── exported_frames/
│   ├── embeddings/
│   ├── elastic_documents/
│   ├── .preprocessing_state_ranczo.json
│   └── ...
└── kiepscy/
    ├── transcoded_videos/
    ├── .preprocessing_state_kiepscy.json
    └── ...
```

**Config struktura:**
```
series_configs/
├── defaults.json          # Domyślne dla wszystkich
├── ranczo.json           # Overrides dla Ranczo
└── kiepscy.json          # Overrides dla Kiepskich
```

**Migracja ze starej struktury:**
```bash
mkdir -p input_data/nazwa_serii
mv input_data/S* input_data/nazwa_serii/
```

---

## Struktura output (per serial)

```
output_data/{series_name}/
├── transcoded_videos/          # MP4 h264_nvenc (720p domyślnie)
├── transcriptions/             # raw/ • clean/ • sound_events/
├── scene_timestamps/           # JSON z timestampami scen
├── exported_frames/            # PNG (1080p domyślnie)
├── embeddings/                 # text/ • video/ • sound_events/ • full_episode/
├── image_hashes/               # perceptual hashes klatek
├── character_detections/       # detections.json + visualizations/ (opcjonalne)
├── character_references_processed/  # face vectors postaci
├── characters/                 # pobrane obrazy referencyjne
├── face_clusters/              # HDBSCAN clusters
├── object_detections/          # D-FINE detections + visualizations/ (opcjonalne)
├── elastic_documents/          # JSONL per typ dokumentu
│   ├── text_segments/
│   ├── text_embeddings/
│   ├── video_frames/
│   └── episode_names/
├── archives/                   # ZIP per odcinek
├── validation_reports/         # JSON raporty walidacji
├── processing_metadata/        # metadata kroków pipeline
├── scraped_pages/              # zapisane strony wiki
├── {series}_episodes.json      # metadane odcinków
├── {series}_characters.json    # lista postaci
└── .preprocessing_state_{series}.json  # stan pipeline (cache)
```

---

## Technologie

| Komponent | Stack |
|-----------|-------|
| Transkodowanie | FFmpeg + h264_nvenc (GPU) |
| Deinterlacing | bwdif (opcjonalnie, auto-detect lub force) |
| Transkrypcja | Whisper large-v3-turbo / ElevenLabs Scribe v1 |
| Sceny | TransNetV2 |
| Embeddingi | Qwen/Qwen3-VL-Embedding-8B (4096-dim) |
| Twarze | InsightFace buffalo_l (112x112) |
| Emocje | EmoNet enet_b2_8 (ONNX) |
| Clustering | HDBSCAN (cuML) |
| Obiekty | D-FINE-X (ustc-community/dfine-xlarge-obj2coco) |
| Image Hashing | Perceptual hashing (pHash) |
| Scraping | Qwen2.5-Coder-7B / Gemini 2.5 Flash |
| Search | Elasticsearch kNN (cosine similarity) |

---

## Parametry konfiguracyjne

**Wszystkie parametry są w `series_configs/*.json`**. Poniżej wartości domyślne z `defaults.json`:

**Transkodowanie (`processing.transcode`):**
```json
{
  "codec": "h264_nvenc",
  "resolution": "720p",
  "video_bitrate_mbps": 2.5,
  "minrate_mbps": 1.5,
  "maxrate_mbps": 3.5,
  "bufsize_mbps": 5.0,
  "audio_bitrate_kbps": 128,
  "gop_size": 2.0,
  "force_deinterlace": false
}
```

**Detekcja scen (`processing.scene_detection`):**
```json
{
  "threshold": 0.5,
  "min_scene_len": 10
}
```

**Eksport klatek (`processing.frame_export`):**
```json
{
  "frames_per_scene": 3
}
```

**Transkrypcja (`processing.transcription`):**
```json
{
  "mode": "whisper",
  "model": "large-v3-turbo",
  "language": "pl",
  "device": "cuda"
}
```

**Scraping (`scraping`):**
```json
{
  "episodes": {
    "parser_mode": "normal",
    "urls": ["https://..."]
  },
  "characters": {
    "parser_mode": "normal",
    "urls": ["https://..."]
  },
  "character_references": {
    "search_engine": "duckduckgo",
    "images_per_character": 5
  }
}
```

**Elasticsearch (`indexing.elasticsearch`):**
```json
{
  "index_name": "nazwa_clips",
  "host": "localhost:9200",
  "dry_run": false,
  "append": false
}
```

**Tryby:**
- `parser_mode`: `"normal"` (Qwen2.5-Coder) | `"premium"` (Gemini 2.5 Flash)
- `transcription.mode`: `"whisper"` | `"elevenlabs"`
- `search_engine`: `"duckduckgo"` | `"google"` (wymaga SERPAPI_API_KEY)

---

## Użycie VRAM

**Target:** ~21GB VRAM (85% z 24GB dla modelu embeddingowego)

**Batch sizes (domyślne):**
- Video embeddings: 32, progress sub-batch: 100
- Text embeddings: 64
- Object detection: 8
- Emotion detection: 32

**Auto-optymalizacja:** Pipeline automatycznie sugeruje optymalny batch size dla 21GB VRAM target

Faktyczne użycie VRAM zależy od:
- Rozdzielczości klatek (domyślnie 1080p dla export, 720p dla transcode)
- Batch size
- Modelu embeddingowego (Qwen3-VL-Embedding-8B z `gpu_memory_utilization=0.85`)
- Concurrent operations

---

## Wolumeny Docker

| Host | Container | Opis |
|------|-----------|------|
| `./input_data` | `/input_data` | Input (read-only) |
| `./output_data` | `/app/output_data` | Output (read-write) |
| `ml_models` (named volume) | `/models` | Modele ML |

**Named volume:** `ranchbot-ai-models` - cache dla:
- HuggingFace (`HF_HOME=/models/huggingface`)
- Torch (`TORCH_HOME=/models/torch`)
- Whisper (`WHISPER_CACHE=/models/whisper`)
- InsightFace (`INSIGHTFACE_HOME=/models/insightface`)
- Ultralytics (`YOLO_CONFIG_DIR=/models/ultralytics`)
- Emotion Model (`EMOTION_MODEL_HOME=/models/emotion_model`)

**Shared memory:** `shm_size: 4gb` (dla PyTorch DataLoader i multiprocessing)

---

## Formaty plików

**Input wideo:** `.mp4` `.avi` `.mkv` `.mov` `.flv` `.wmv` `.webm`
**Output wideo:** `.mp4` (h264_nvenc, 720p domyślnie)
**Output klatki:** `.png` (1080p domyślnie)
**Nazewnictwo odcinków:** `S01E01`, `s01e12`, `S10E05` (case-insensitive)
**Nazewnictwo folderów:** `S01`, `Sezon 1`, `Season 10` → autonormalizacja do `SXX`
**Metadane:** JSON (`{series}_episodes.json`, `{series}_characters.json`)
**Elastic docs:** JSONL per typ (`text_segments`, `video_frames`, `text_embeddings`, `episode_names`)

---

## State Management

Pipeline automatycznie zapisuje stan przetwarzania w `.preprocessing_state_{series}.json`:
- Śledzi które kroki zostały ukończone dla każdego odcinka
- Pozwala na wznowienie po przerwaniu (Ctrl+C)
- Pomija już przetworzone odcinki (chyba że `--force-rerun`)

**Resetowanie stanu:**
```bash
rm output_data/ranczo/.preprocessing_state_ranczo.json
```

---

## Instalacja

```bash
# NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# Test
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

---

## Troubleshooting

```bash
# Logi
docker logs -f preprocessor-preprocessor-run-XXX

# GPU check
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi

# OOM na GPU
# Zmniejsz batch_size w series_configs/{series}.json

# Brak miejsca na dysku
docker system prune -a
docker volume prune
du -sh output_data/*

# Wznów pipeline po przerwaniu
./run-preprocessor.sh run-all --series nazwa_serii
# Stan jest automatycznie przywracany z .preprocessing_state_{series}.json

# Reset stanu dla konkretnego serialu
rm output_data/nazwa_serii/.preprocessing_state_nazwa_serii.json

# Reset całego named volume z modelami
docker volume rm ranchbot-ai-models

# Shell w kontenerze
./run-preprocessor.sh bash

# Debug - wizualizacja grafu pipeline
./run-preprocessor.sh visualize --series nazwa_serii
```

---

## Search Guide

Szczegółowy opis funkcjonalności search znajduje się w `SEARCH_GUIDE.md`.

**Quick examples:**
```bash
# Statystyki
./run-preprocessor.sh search --series ranczo --stats

# Full-text search
./run-preprocessor.sh search --series ranczo --text "Lucy Wilska" --season 10

# Semantic search
./run-preprocessor.sh search --series ranczo --text-semantic "wesele"

# Visual search
./run-preprocessor.sh search --series ranczo --image /input_data/screenshot.jpg

# Search by character/emotion/object
./run-preprocessor.sh search --series ranczo --character "Lucy Wilska" --emotion "happiness"
./run-preprocessor.sh search --series ranczo --object "person:5+"

# Lista postaci
./run-preprocessor.sh search --series ranczo --list-characters
```

---

## Tworzenie nowego serialu

1. **Przygotuj dane:**
   ```bash
   mkdir -p input_data/nowy_serial/S01
   cp /path/to/videos/*.mp4 input_data/nowy_serial/S01/
   ```

2. **Stwórz config:**
   ```bash
   cp series_configs/defaults.json series_configs/nowy_serial.json
   ```

3. **Edytuj config:**
   ```json
   {
     "series_name": "nowy_serial",
     "display_name": "Nowy Serial",
     "indexing": {
       "elasticsearch": {
         "index_name": "nowy_serial_clips"
       }
     },
     "scraping": {
       "episodes": {
         "urls": ["https://..."]
       },
       "characters": {
         "urls": ["https://..."]
       }
     }
   }
   ```

4. **Uruchom pipeline:**
   ```bash
   ./run-preprocessor.sh run-all --series nowy_serial
   ```

---

## API Keys (opcjonalne)

Ustaw w `.env` lub docker-compose environment:

```bash
# ElevenLabs (dla premium transcription)
ELEVEN_API_KEY=your_key

# Google Images (dla premium character references)
SERPAPI_API_KEY=your_key

# Gemini (dla premium scraping)
GEMINI_API_KEY=your_key

# Elasticsearch (jeśli wymaga auth)
ES_HOST=localhost:9200
ES_USER=elastic
ES_PASS=password
```

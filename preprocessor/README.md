# Video Preprocessing Pipeline

Docker pipeline do przetwarzania wideo z GPU: transkodowanie, transkrypcja, detekcja scen, rozpoznawanie postaci, embeddingi → Elasticsearch.

**Wymagania:** GPU z CUDA (RTX 3090 24GB zalecane) • NVIDIA Container Toolkit • Docker Compose

---

## Quick Start

```bash
cd preprocessor
mkdir -p input_data/videos output_data
cp /twoje/wideo/*.mp4 input_data/videos/
docker compose build

# Pełny pipeline z scrapingiem
./run-preprocessor.sh run-all /input_data/ranczo \
  --scrape-urls https://example.com/wiki/Seria \
  --character-urls https://example.com/wiki/Postacie \
  --series-name ranczo

# Z gotowymi metadanymi
./run-preprocessor.sh run-all /input_data/kiepscy \
  --episodes-info-json /input_data/kiepscy_episodes.json \
  --series-name kiepscy

# Pomiń transkodowanie i transkrypcję (użyj istniejących)
./run-preprocessor.sh run-all /input_data/videos \
  --episodes-info-json /input_data/episodes.json \
  --series-name nazwa_serii \
  --skip-transcode \
  --skip-transcribe

# Tryb premium (Gemini + ElevenLabs + Google Images)
./run-preprocessor.sh run-all /input_data/videos \
  --series-name nazwa_serii \
  --parser-mode premium \
  --transcription-mode premium \
  --search-mode premium
```

---

## Pipeline (13 kroków)

```
SCRAPING          PROCESSING                              INDEXING
───────────────────────────────────────────────────────────────────────
[0a] episodes  ─┬→ [1] transcode → [2] transcribe → [3] separate sounds
[0b] characters │  [4] analyze text
[0c] download   │  [5] detect scenes → [6] export frames
[0d] process   ─┘  [7] text embeddings
                   [8] frame processing (8a-8f)
                   [9] elastic docs → [10] archives → [11] index → [12] validate
```

---

## Flagi Skip

| Flaga | Krok |
|-------|------|
| `--skip-transcode` | 1: Transkodowanie |
| `--skip-transcribe` | 2-3: Transkrypcja + separacja |
| `--skip-text-analysis` | 4: Analiza tekstu |
| `--skip-scenes` | 5: Detekcja scen |
| `--skip-frame-export` | 6: Eksport klatek |
| `--skip-embeddings` | 7: Text embeddings |
| `--skip-character-reference-processing` | 0d: Przetwarzanie referencji postaci |
| `--skip-elastic-documents` | 9: Dokumenty ES |
| `--skip-archives` | 10: Archiwizacja ZIP |
| `--skip-index` | 11: Indeksowanie |
| `--skip-validation` | 12: Walidacja |

<details>
<summary>Flagi frame processing (8a-8f)</summary>

| Flaga | Krok |
|-------|------|
| `--skip-image-hashing` | 8a: Image hashing |
| `--skip-video-embeddings` | 8b: Video embeddings |
| `--skip-character-detection` | 8c: Character detection |
| `--skip-emotion-detection` | 8d: Emotion detection |
| `--skip-face-clustering` | 8e: Face clustering |
| `--skip-object-detection` | 8f: Object detection |

**Uwaga:** Wizualizacje są domyślnie wyłączone. Użyj `--debug-visualizations` aby je włączyć.

</details>

**Premium modes:** `--parser-mode premium` (Gemini 2.5 Flash) • `--transcription-mode premium` (ElevenLabs) • `--search-mode premium` (Google Images)

---

## Główne komendy

```bash
# Pełny pipeline
./run-preprocessor.sh run-all /input_data/videos --series-name nazwa_serii [OPTIONS]

# Pojedyncze kroki
./run-preprocessor.sh scrape-episodes --urls URL --output-file /input_data/episodes.json
./run-preprocessor.sh transcode /input_data/videos [--episodes-info-json FILE] [--resolution 720p]
./run-preprocessor.sh transcribe /input_data/videos --name series --episodes-info-json FILE
./run-preprocessor.sh transcribe-elevenlabs /input_data/videos --name series --episodes-info-json FILE
./run-preprocessor.sh separate-sounds --transcription-jsons /app/output_data/transcriptions
./run-preprocessor.sh analyze-text --season S10 --language pl
./run-preprocessor.sh detect-scenes /input_data/videos [--threshold 0.5]
./run-preprocessor.sh export-frames /input_data/videos
./run-preprocessor.sh process-character-references --name series
./run-preprocessor.sh image-hashing --frames-dir /app/output_data/exported_frames
./run-preprocessor.sh generate-embeddings --transcription-jsons /app/output_data/transcriptions
./run-preprocessor.sh generate-elastic-documents --transcription-jsons /app/output_data/transcriptions
./run-preprocessor.sh generate-archives --series-name nazwa_serii
./run-preprocessor.sh index --name nazwa_serii
./run-preprocessor.sh validate --season S01 --series-name nazwa_serii

# Narzędzia
./run-preprocessor.sh search --text "query"
./run-preprocessor.sh search --text-semantic "query"
./run-preprocessor.sh search --image /path/to/image.jpg
./run-preprocessor.sh search --character "Nazwa"
./run-preprocessor.sh search --emotion "happiness"
./run-preprocessor.sh search --stats
./run-preprocessor.sh fix-unicode --transcription-jsons DIR --episodes-info-json FILE --name series
./run-preprocessor.sh import-transcriptions --input-dir DIR --episodes-info-json FILE --name series
```

---

## Multi-Series Support

Pipeline wspiera przetwarzanie wielu seriali jednocześnie. Każdy serial ma dedykowany folder:

**Input struktura:**
```
input_data/
├── ranczo/
│   ├── S01/
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
│   ├── ranczo_episodes.json
│   ├── ranczo_characters.json
│   └── ...
└── kiepscy/
    ├── transcoded_videos/
    ├── kiepscy_episodes.json
    └── ...
```

**Migracja ze starej struktury:**
```bash
mkdir -p input_data/{series_name}
mv input_data/S* input_data/{series_name}/
```

---

## Struktura output (per serial)

```
output_data/{series_name}/
├── transcoded_videos/          # MP4 h264_nvenc (720p)
├── transcriptions/             # raw/ • clean/ • sound_events/
├── scene_timestamps/           # JSON z timestampami scen
├── exported_frames/            # JPG 1080p (domyślnie)
├── embeddings/                 # text • video • sound_events • full_episode
├── image_hashes/               # perceptual hashes klatek
├── character_detections/       # detections.json + visualizations/ (opcjonalne)
├── character_references_processed/  # face vectors postaci
├── characters/                 # pobrane obrazy referencyjne
├── face_clusters/              # HDBSCAN clusters
├── object_detections/          # D-FINE detections + visualizations/ (opcjonalne)
├── elastic_documents/          # JSONL per typ dokumentu
├── archives/                   # ZIP per odcinek
├── validation_reports/         # JSON raporty walidacji
├── processing_metadata/        # metadata kroków pipeline
└── scraped_pages/              # zapisane strony wiki
```

---

## Technologie

| Komponent | Stack |
|-----------|-------|
| Transkodowanie | FFmpeg + h264_nvenc (GPU) |
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

## Użycie VRAM

**Target:** ~21GB VRAM (85% z 24GB dla modelu embeddingowego)

**Batch sizes:**
- Video embeddings: 32 (domyślnie), progress sub-batch: 100
- Text embeddings: 64 (domyślnie)
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

**Input:** `.mp4` `.avi` `.mkv` `.mov` `.flv` `.wmv` `.webm`
**Output wideo:** `.mp4` (h264_nvenc, 720p domyślnie)
**Output klatki:** `.jpg` (1080p domyślnie)
**Nazewnictwo odcinków:** `S01E01`, `s01e12`, `S10E05` (case-insensitive)
**Nazewnictwo folderów:** `S01`, `Sezon 1`, `Season 10` → autonormalizacja do `SXX`
**Metadane:** JSON (episodes.json, characters.json)
**Elastic docs:** JSONL per typ (text_segments, video_frames, etc.)

---

## Parametry konfiguracyjne

**Transkodowanie:**
- Target file size: 50MB per 100s
- Audio bitrate: 128 kbps
- GOP size: 0.5s

**Scene detection:**
- Threshold: 0.5
- Min scene length: 10 frames

**Text chunking:**
- Segments per embedding: 5
- Sentences per chunk: 8
- Chunk overlap: 3

**Character detection:**
- Reference images per character: 3
- Normalized face size: 112x112
- Face detection threshold: 0.2
- Reference matching threshold: 0.50
- Frame detection threshold: 0.55

**Object detection:**
- Confidence threshold: 0.30

**Embeddings:**
- Dimension: 4096
- Max model length: 8192 tokens
- Chunked prefill: enabled

---

## Dodatkowe opcje

**State management:**
- `--no-state` - wyłącz zapisywanie stanu (brak wznowienia po przerwaniu)
- Domyślnie pipeline zapisuje stan i można wznowić po Ctrl+C

**Ramdisk:**
- `--ramdisk-path /mnt/ramdisk` - użyj RAMdisk dla tymczasowych plików (szybsze przetwarzanie)
- Domyślnie: `/dev/shm` (shared memory, 4GB z docker-compose)
- RAMdisk używany do: kopiowania klatek podczas frame processing, tymczasowych plików transkrypcji

**Interaktywny tryb:**
- `--interactive-character-processing` - manualna selekcja twarzy przy przetwarzaniu referencji postaci

**Debug:**
- `--debug-visualizations` - włącz wizualizacje dla detekcji postaci i obiektów (wyłączone domyślnie)
- `--dry-run` - test indeksowania bez wysyłania do Elasticsearch

**Embeddingi:**
- `--skip-full-episode` - pomiń generowanie embeddingów całych odcinków (tylko text, video, sound events)
- `--batch-size N` - rozmiar batcha dla embeddingów (domyślnie 32 dla video, 64 dla text)

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
docker logs ranchbot-preprocessing-app -f

# GPU check
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi

# OOM na GPU → zmniejsz batch size
./run-preprocessor.sh generate-embeddings --batch-size 16  # domyślnie 32

# Brak miejsca na dysku
docker system prune -a
docker volume prune
du -sh output_data/*  # sprawdź co zajmuje miejsce

# Wznów pipeline po przerwaniu
./run-preprocessor.sh run-all /input_data/videos --series-name nazwa_serii --name nazwa_serii

# Reset całego named volume z modelami
docker volume rm ranchbot-ai-models

# Shell w kontenerze
./run-preprocessor.sh bash
```

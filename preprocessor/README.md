# Video Preprocessing Pipeline

Docker pipeline do przetwarzania wideo z GPU: transkodowanie, transkrypcja, detekcja scen, rozpoznawanie postaci, embeddingi → Elasticsearch.

**Wymagania:** RTX 3090 (24GB) • 64GB RAM • 150GB SSD • NVIDIA Container Toolkit

---

## Quick Start

```bash
mkdir -p input_data/videos output_data
cp /twoje/wideo/*.mp4 input_data/videos/
docker-compose build

# Pełny pipeline
./run-preprocessor.sh run-all /input_data/videos \
  --scrape-urls https://example.com/wiki/Seria \
  --character-urls https://example.com/wiki/Postacie \
  --series-name nazwa_serii

# Z gotowymi danymi (skip transkodowanie + transkrypcja)
./run-preprocessor.sh run-all /input_data/transcoded_videos \
  --episodes-info-json /input_data/episodes.json \
  --series-name nazwa_serii \
  --skip-transcode --skip-transcribe
```

---

## Pipeline (14 kroków)

```
SCRAPING          PROCESSING                              INDEXING
───────────────────────────────────────────────────────────────────────
[0a] episodes  ─┬→ [1] transcode → [2] transcribe → [3] separate sounds
[0b] characters │  [4] analyze text
[0c] download   │  [5] detect scenes → [6] export frames
[0d] process   ─┘  [7] text embeddings
                   [8] frame processing (8a-8h)
                   [9] elastic docs → [10] archives → [11] index → [12] validate
```

**Wydajność:** ~30 min/odcinek (45 min) • ~2-3 odcinki/godz

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
| `--skip-frame-processing` | 8: Wszystkie (8a-8h) |
| `--skip-elastic-documents` | 9: Dokumenty ES |
| `--skip-archives` | 10: Archiwizacja ZIP |
| `--skip-index` | 11: Indeksowanie |
| `--skip-validation` | 12: Walidacja |

<details>
<summary>Flagi frame processing (8a-8h)</summary>

| Flaga | Krok |
|-------|------|
| `--skip-image-hashing` | 8a |
| `--skip-video-embeddings` | 8b |
| `--skip-character-detection` | 8c |
| `--skip-character-visualization` | 8d |
| `--skip-emotion-detection` | 8e |
| `--skip-face-clustering` | 8f |
| `--skip-object-detection` | 8g |
| `--skip-object-visualization` | 8h |
| `--skip-character-reference-processing` | 0d |

</details>

**Premium modes:** `--parser-mode premium` (Gemini) • `--transcription-mode premium` (ElevenLabs) • `--search-mode premium` (Google Images)

---

## Główne komendy

```bash
# Pojedyncze kroki
./run-preprocessor.sh scrape-episodes --urls URL --output-file /input_data/episodes.json
./run-preprocessor.sh transcode /input_data/videos --episodes-info-json /input_data/episodes.json
./run-preprocessor.sh transcribe /input_data/videos --name series --model large-v3-turbo
./run-preprocessor.sh separate-sounds --transcription-jsons /app/output_data/transcriptions
./run-preprocessor.sh analyze-text --season S10 --language pl
./run-preprocessor.sh detect-scenes /input_data/videos --threshold 0.5
./run-preprocessor.sh export-frames /input_data/videos --scene-timestamps-dir /app/output_data/scene_timestamps
./run-preprocessor.sh process-character-references --name series
./run-preprocessor.sh generate-embeddings --transcription-jsons /app/output_data/transcriptions
./run-preprocessor.sh generate-elastic-documents --transcription-jsons /app/output_data/transcriptions
./run-preprocessor.sh generate-archives --series-name ranczo [--force-regenerate] [--allow-partial]
./run-preprocessor.sh index --name series --elastic-documents-dir /app/output_data/elastic_documents

# Wyszukiwanie
./run-preprocessor.sh search --text "query"
./run-preprocessor.sh search --text-semantic "query"
./run-preprocessor.sh search --image /path/to/image.jpg
./run-preprocessor.sh search --character "Nazwa"
./run-preprocessor.sh search --emotion "happiness"
./run-preprocessor.sh search --stats
```

---

## Struktura output

```
output_data/
├── transcoded_videos/          # MP4 h264_nvenc
├── transcriptions/             # raw/ • clean/ • sound_events/
├── scene_timestamps/           # JSON
├── exported_frames/            # JPG 1080p
├── embeddings/                 # text • video • sound_events • full_episode
├── character_detections/       # detections.json + visualizations/
├── character_references_processed/  # face vectors
├── face_clusters/              # HDBSCAN clusters
├── object_detections/          # D-FINE detections
├── elastic_documents/          # JSONL per typ
├── archives/                   # ZIP per odcinek
└── validation_reports/         # JSON
```

---

## Technologie

| Komponent | Stack |
|-----------|-------|
| Transkodowanie | FFmpeg 7 + NVENC |
| Transkrypcja | Whisper large-v3-turbo |
| Sceny | TransNetV2 |
| Embeddingi | Qwen3-VL-Embedding-8B |
| Twarze | InsightFace (buffalo_l) |
| Emocje | FER+ ONNX |
| Clustering | HDBSCAN (cuML) |
| Obiekty | D-FINE-X |
| Scraping | Qwen2.5-Coder-7B |
| Search | Elasticsearch kNN |

---

## VRAM (RTX 3090)

| Operacja | VRAM |
|----------|------|
| Transcode | ~2GB |
| Whisper | ~3GB |
| TransNetV2 | ~2GB |
| Embeddings (batch=32) | ~10GB |
| InsightFace | ~1GB |
| LLM scraping | ~8GB |
| **Peak** | **~12GB** |

---

## Wolumeny Docker

| Host | Container | Tryb |
|------|-----------|------|
| `input_data/` | `/input_data` | ro |
| `output_data/` | `/app/output_data` | rw |
| `ml_models` (named) | `/models` | ~25GB |

---

## Formaty plików

**Input:** `.mp4` `.avi` `.mkv` `.mov` `.flv` `.wmv` `.webm`  
**Output:** `.mp4` (h264_nvenc)  
**Nazewnictwo:** `S01E01` lub `s01e12` (case-insensitive)  
**Foldery:** `S01`, `Sezon 1`, `Season 10` → autonormalizacja do `SXX`

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
docker logs ranchbot-preprocessing-app -f          # Logi
nvidia-smi                                         # GPU check
./run-preprocessor.sh generate-embeddings --batch-size 14  # OOM → mniejszy batch
docker system prune -a && docker volume prune      # Brak miejsca
```
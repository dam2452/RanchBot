# Video Preprocessing Pipeline

Docker app do przetwarzania wideo z GPU (NVIDIA): transkodowanie, transkrypcja (Whisper/ElevenLabs), detekcja scen, eksport klatek, wykrywanie postaci, embeddingi i indeksowanie w Elasticsearch.

## Wymagania sprzętowe

**Jedyna wspierana konfiguracja:** RTX 3090 (24GB VRAM) + 64GB RAM + 150GB+ SSD NVMe

Wszystkie domyślne ustawienia (batch_size=32, 1080p frames) są skalibrowane pod tę konfigurację. Brak fallbacku na CPU.

## Quick Start

```bash
cd preprocessor
mkdir -p input_data/videos output_data
cp /twoje/wideo/*.mp4 input_data/videos/
docker-compose build

# Pełny pipeline
./run-preprocessor.sh run-all /input_data/videos \
  --scrape-urls https://example.com/wiki/Seria_I \
  --character-urls https://example.com/wiki/Lista_postaci \
  --series-name nazwa_serii

# Z gotową transkrypcją i transkodowaniem
./run-preprocessor.sh run-all /input_data/transcoded_videos \
  --episodes-info-json /input_data/episodes.json \
  --series-name nazwa_serii \
  --skip-transcode --skip-transcribe
```

## Architektura pipeline (11 kroków)

```
[0a] scrape episodes → [1] transcode → [2] transcribe → [3] detect scenes
[0b] scrape characters → [0c] download references
[4] export frames → [5] text embeddings → [6] frame processing:
    [6a] image hashing | [6b] video embeddings | [6c] character detection
    [6d] object detection | [6e] object visualization
[7] generate elastic docs → [8] index
```

**Czas:** ~28-32 min na 45-min odcinek | **Throughput:** ~2-3 odcinki/godz

## Flagi skip dla run-all

| Flaga | Krok |
|-------|------|
| `--skip-transcode` | 1/9: Transkodowanie |
| `--skip-transcribe` | 2/9: Transkrypcja |
| `--skip-scenes` | 3/9: Detekcja scen |
| `--skip-frame-export` | 4/9: Eksport klatek |
| `--skip-embeddings` | 5/9: Text embeddings |
| `--skip-frame-processing` | 6/9: Wszystkie sub-kroki |
| `--skip-image-hashing` | 6a: Image hashing |
| `--skip-video-embeddings` | 6b: Video embeddings |
| `--skip-character-detection` | 6c: Character detection |
| `--skip-object-detection` | 6d: Object detection |
| `--skip-object-visualization` | 6e: Object visualization |
| `--skip-elastic-documents` | 7/9: Generowanie dokumentów |
| `--skip-index` | 8/9: Indeksowanie |

**Premium modes:** `--parser-mode premium` (Gemini), `--transcription-mode premium` (ElevenLabs), `--search-mode premium` (Google Images)

## Główne komendy CLI

```bash
# Scraping metadanych
./run-preprocessor.sh scrape-episodes --urls URL1 --urls URL2 --output-file /input_data/episodes.json

# Transkodowanie
./run-preprocessor.sh transcode /input_data/videos --episodes-info-json /input_data/episodes.json

# Transkrypcja
./run-preprocessor.sh transcribe /input_data/videos --name series_name --model large-v3-turbo

# Detekcja scen
./run-preprocessor.sh detect-scenes /input_data/videos --threshold 0.5

# Eksport klatek
./run-preprocessor.sh export-frames /input_data/videos --scene-timestamps-dir /app/output_data/scene_timestamps

# Embeddingi (domyślnie sentence-based: 8 zdań + 3 overlap)
./run-preprocessor.sh generate-embeddings --transcription-jsons /app/output_data/transcriptions --frames-dir /app/output_data/frames_1080p

# Indeksowanie
./run-preprocessor.sh index --name series_name --elastic-documents-dir /app/output_data/elastic_documents

# Wyszukiwanie
./run-preprocessor.sh search --text "query" --limit 5
./run-preprocessor.sh search --text-semantic "query"
./run-preprocessor.sh search --image /path/to/image.jpg
./run-preprocessor.sh search --stats
```

## Zużycie VRAM (RTX 3090)

| Operacja | VRAM |
|----------|------|
| Transcode (NVENC) | ~2GB |
| Whisper large-v3-turbo | ~3GB |
| TransNetV2 | ~2GB |
| Embeddings (batch=32) | ~10GB |
| InsightFace | ~1GB |
| LLM scraping (Qwen 8-bit) | ~8GB |
| **Peak łącznie** | **~12GB** |

## Wolumeny Docker

| Host | Container | Tryb |
|------|-----------|------|
| `input_data/` | `/input_data` | read-only |
| `output_data/` | `/app/output_data` | read-write |
| `ml_models` (named) | `/models` | persistent (~25GB) |

## Technologie

| Komponent | Technologia                          |
|-----------|--------------------------------------|
| Transkodowanie | Jellyfin FFmpeg 7 + NVENC            |
| Transkrypcja | Whisper large-v3-turbo (CTranslate2) |
| Detekcja scen | TransNetV2                           |
| Embeddingi | Qwen3-VL-Embedding-8B                |
| Face recognition | InsightFace (buffalo_l)              |
| Object detection | D-FINE-X                             |
| LLM scraping | Qwen2.5-Coder-7B-Instruct            |
| Search | Elasticsearch (kNN + HNSW)           |

## Format plików wideo

**Wejście:** `.mp4`, `.avi`, `.mkv`, `.mov`, `.flv`, `.wmv`, `.webm`
**Wyjście:** `.mp4` (h264_nvenc)
**Nazewnictwo:** `S01E01` lub `s01e12` (case-insensitive)

## Instalacja

Wymagania: Docker 20.10+, Docker Compose 1.29+, NVIDIA Container Toolkit, NVIDIA Driver 525+

```bash
# Instalacja NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# Weryfikacja
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

## Troubleshooting

```bash
# Logi
docker logs ranchbot-preprocessing-app -f

# GPU check
nvidia-smi
docker-compose run --rm preprocessor ffmpeg -encoders | grep nvenc

# CUDA OOM - zmniejsz batch size
./run-preprocessor.sh generate-embeddings --batch-size 14  # dla ~16GB VRAM

# Brak miejsca
docker system prune -a && docker volume prune
```

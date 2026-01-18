# Video Preprocessing Pipeline

Docker app do przetwarzania wideo z GPU (NVIDIA): transkodowanie, transkrypcja (Whisper/ElevenLabs), detekcja scen, eksport klatek, wykrywanie postaci, klasteryzacja twarzy, embeddingi i indeksowanie w Elasticsearch.

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

## Architektura pipeline (12 kroków)

```
[0a] scrape episodes → [1] transcode → [2] transcribe → [3] analyze text
[0b] scrape characters → [0c] download references
[4] detect scenes → [5] export frames → [6] text embeddings → [7] frame processing:
    [7a] image hashing | [7b] video embeddings | [7c] character detection
    [7d] character visualization | [7e] face clustering | [7f] object detection
    [7g] object visualization
[8] generate elastic docs → [9] archive zips → [10] index → [11] validate
```

**Czas:** ~28-32 min na 45-min odcinek | **Throughput:** ~2-3 odcinki/godz

## Flagi skip dla run-all

| Flaga | Krok |
|-------|------|
| `--skip-transcode` | 1/12: Transkodowanie |
| `--skip-transcribe` | 2/12: Transkrypcja |
| `--skip-text-analysis` | 3/12: Analiza tekstowa |
| `--skip-scenes` | 4/12: Detekcja scen |
| `--skip-frame-export` | 5/12: Eksport klatek |
| `--skip-embeddings` | 6/12: Text embeddings |
| `--skip-frame-processing` | 7/12: Wszystkie sub-kroki |
| `--skip-image-hashing` | 7a: Image hashing |
| `--skip-video-embeddings` | 7b: Video embeddings |
| `--skip-character-detection` | 7c: Character detection |
| `--skip-character-visualization` | 7d: Character visualization |
| `--skip-face-clustering` | 7e: Face clustering |
| `--skip-object-detection` | 7f: Object detection |
| `--skip-object-visualization` | 7g: Object visualization |
| `--skip-elastic-documents` | 8/12: Generowanie dokumentów |
| `--skip-archives` | 9/12: Archiwizacja ZIP |
| `--skip-index` | 10/12: Indeksowanie |
| `--skip-validation` | 11/12: Walidacja outputu |

**Uwaga:** Walidacja (krok 11/12) działa tylko dla sezonów, które mają pliki wideo w katalogu wejściowym (`input_data/videos`). Puste foldery sezonów są skipowane automatycznie. Nazwy folderów są normalizowane do formatu SXX (np. "Sezon 10" → "S10", "season 3" → "S03").

**Premium modes:** `--parser-mode premium` (Gemini), `--transcription-mode premium` (ElevenLabs), `--search-mode premium` (Google Images)

## Główne komendy CLI

```bash
# Scraping metadanych
./run-preprocessor.sh scrape-episodes --urls URL1 --urls URL2 --output-file /input_data/episodes.json

# Transkodowanie
./run-preprocessor.sh transcode /input_data/videos --episodes-info-json /input_data/episodes.json

# Transkrypcja
./run-preprocessor.sh transcribe /input_data/videos --name series_name --model large-v3-turbo

# Analiza tekstowa transkrypcji (generuje text_stats.json + elastic text_statistics.jsonl)
./run-preprocessor.sh analyze-text --season S10 --language pl
# Statystyki: zdania, slowa, unikalne slowa, bigramy, trigramy, czestotliwosc slow

# Detekcja scen
./run-preprocessor.sh detect-scenes /input_data/videos --threshold 0.5

# Eksport klatek
./run-preprocessor.sh export-frames /input_data/videos --scene-timestamps-dir /app/output_data/scene_timestamps

# Embeddingi (domyślnie sentence-based: 8 zdań + 3 overlap + full episode)
./run-preprocessor.sh generate-embeddings --transcription-jsons /app/output_data/transcriptions --frames-dir /app/output_data/frames_1080p
# Generuje 3 pliki: embeddings_text.json, embeddings_video.json, embeddings_full_episode.json
# Full episode embedding używa sliding window (6000 chars, 4500 overlap) dla długich transkryptów

# Generowanie dokumentow Elasticsearch
./run-preprocessor.sh generate-elastic-documents --transcription-jsons /app/output_data/transcriptions
# Typy: segments, text_embeddings, video_embeddings, episode_names, text_statistics, full_episode_embeddings

# Archiwizacja dokumentow Elasticsearch (ZIP per odcinek)
./run-preprocessor.sh generate-archives --series-name ranczo
# Generuje: output_data/archives/S01/E01/ranczo_S01E01_elastic_documents.zip
# Zawiera: segments, text_embeddings, video_embeddings, episode_name, text_statistics, full_episode_embeddings
# UWAGA: Domyslnie tworzy ZIP tylko gdy wszystkie 6 plikow jest gotowych!
./run-preprocessor.sh generate-archives --season 1 --episode 1  # tylko jeden odcinek
./run-preprocessor.sh generate-archives --force-regenerate  # nadpisz istniejace
./run-preprocessor.sh generate-archives --allow-partial  # tworz ZIP nawet jesli brakuje plikow

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

## Struktura output_data

```
output_data/
├── transcoded_videos/     # MP4 h264_nvenc
├── transcriptions/        # JSON segmented + text_stats.json
├── scene_timestamps/      # JSON ze scenami
├── exported_frames/       # JPG 1080p
├── embeddings/            # embeddings_text.json, embeddings_video.json, embeddings_full_episode.json
├── image_hashes/          # perceptual hashes klatek
├── character_detections/  # detections.json (InsightFace) + visualizations/
├── face_clusters/         # klastry twarzy (HDBSCAN)
├── object_detections/     # detections.json (D-FINE) + visualizations/
├── elastic_documents/     # JSONL dla każdego typu i odcinka
│   ├── segments/
│   ├── text_embeddings/
│   ├── video_embeddings/
│   ├── episode_names/
│   ├── text_statistics/
│   └── full_episode_embeddings/
├── archives/              # ZIP (wszystkie JSONL per odcinek)
│   └── S01/E01/ranczo_S01E01_elastic_documents.zip
└── validation_reports/    # JSON z raportami walidacji
```

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
| Face clustering | HDBSCAN (cuML GPU)                   |
| Object detection | D-FINE-X                             |
| LLM scraping | Qwen2.5-Coder-7B-Instruct            |
| Search | Elasticsearch (kNN + HNSW)           |

## Nowe funkcje

### Face Clustering (7e)
Automatyczna klasteryzacja wykrytych twarzy za pomocą HDBSCAN:
- **GPU-only:** cuML HDBSCAN (wymaga CUDA)
- **Parametry:** `min_cluster_size=5`, `min_samples=3` (konfigurowalne w settings)
- **Output:** face_clusters/{season}/{episode}/ z plikami JSON i opcjonalnie pełnymi klatkami
- **Skip flag:** `--skip-face-clustering`

### Character Detection Visualization (7d)
Wizualizacja wykrytych postaci na klatkach:
- **Output:** character_detections/visualizations/ z adnotowanymi klatkami
- **Skip flag:** `--skip-character-visualization`

### Full Episode Embedding (6)
Generowanie embeddingi dla całego transkryptu odcinka:
- **Sliding window:** 6000 chars per chunk, 4500 chars overlap dla długich transkryptów
- **Weighted averaging:** chunks ważone długością
- **Normalizacja:** L2 normalization finalnego embeddingu
- **Output:** embeddings_full_episode.json + elastic document w full_episode_embeddings/
- **Config:** `settings.embedding.generate_full_episode_embedding = True` (domyślnie)

## Format plików wideo

**Wejście:** `.mp4`, `.avi`, `.mkv`, `.mov`, `.flv`, `.wmv`, `.webm`
**Wyjście:** `.mp4` (h264_nvenc)
**Nazewnictwo plików:** `S01E01` lub `s01e12` (case-insensitive)
**Nazewnictwo folderów:** `S01`, `S10` (lub `Sezon 1`, `Season 10` - automatycznie normalizowane)

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

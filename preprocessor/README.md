# Video Preprocessing Pipeline

Aplikacja Docker do przetwarzania wideo z akceleracją GPU (NVIDIA): transkodowanie, transkrypcja (Whisper/ElevenLabs), detekcja scen, eksport klatek, wykrywanie postaci, generowanie embeddingów i indeksowanie w Elasticsearch.

---

## ⚠️ Wymagania sprzętowe

> **UWAGA: Ta aplikacja została zaprojektowana, zoptymalizowana i przetestowana WYŁĄCZNIE na RTX 3090 (24GB VRAM) + 64GB RAM.**
>
> Wszystkie domyślne ustawienia (batch size=28, VRAM usage, cache) są skalibrowane pod tę konkretną konfigurację.
> Uruchomienie na innym sprzęcie wymaga manualnego dostosowania parametrów i może nie działać poprawnie.

| Komponent | **Konfiguracja testowa (jedyna wspierana)** |
|-----------|-------------------------------------------|
| **GPU** | **RTX 3090 24GB** |
| **VRAM** | **24GB** |
| **RAM** | **64GB** |
| **Dysk** | **150GB+ SSD NVMe** |

**Aplikacja działa TYLKO na GPU NVIDIA. Brak fallbacku na CPU.**

### Specyfikacja RTX 3090 + 64GB RAM

- **Batch size 28** dla embeddingów wykorzystuje ~10GB z 24GB VRAM
- **Pełne cache modeli** (~25GB) trzymane w RAMie bez swapowania
- **Bez OOM** przy równoczesnym działaniu Ollamy i preprocessora
- **NVENC hardware encoding** dla 1080p h264

### Zużycie VRAM (RTX 3090 - 24GB)

| Operacja                       | VRAM | Konfiguracja |
|--------------------------------|------|--------------|
| Transcode (NVENC)              | ~2GB | h264_nvenc preset slow |
| Whisper large-v3-turbo         | ~3GB | CTranslate2 float16 |
| TransNetV2                     | ~2GB | PyTorch CUDA |
| **Embeddings (batch_size=28)** | **~10GB** | **Domyślne dla RTX 3090** |
| InsightFace (buffalo_l)        | ~1GB | ArcFace face recognition |
| LLM scraping (Qwen 8-bit)      | ~8GB | Ollama 8-bit quantization |
| **Peak łącznie**               | **~12GB** | **Połowa VRAM 3090 = margines bezpieczeństwa** |

---

## Quick Start

### Pełny pipeline (od zera)

```bash
cd preprocessor
mkdir -p input_data/videos output_data
cp /twoje/wideo/*.mp4 input_data/videos/

docker-compose build

../run-preprocessor.sh run-all /input_data/videos \
  --scrape-urls https://ranczo.fandom.com/wiki/Seria_I \
  --character-urls https://ranczo.fandom.com/wiki/Lista_postaci \
  --series-name ranczo

docker logs ranchbot-preprocessing-app -f
```

### Z gotową transkrypcją i transkodowaniem

```bash
../run-preprocessor.sh detect-scenes /input_data/videos

../run-preprocessor.sh export-frames /input_data/videos \
  --episodes-info-json /input_data/episodes.json \
  --scene-timestamps-dir /app/output_data/scene_timestamps \
  --name ranczo

../run-preprocessor.sh image-hashing \
  --frames-dir /app/output_data/frames \
  --episodes-info-json /input_data/episodes.json \
  --name ranczo

../run-preprocessor.sh generate-embeddings \
  --transcription-jsons /app/output_data/transcriptions \
  --videos /input_data/videos \
  --scene-timestamps-dir /app/output_data/scene_timestamps

../run-preprocessor.sh generate-elastic-documents \
  --transcription-jsons /app/output_data/transcriptions \
  --embeddings-dir /app/output_data/embeddings \
  --scene-timestamps-dir /app/output_data/scene_timestamps \
  --name ranczo

../run-preprocessor.sh index --name ranczo \
  --transcription-jsons /app/output_data/transcriptions
```

---

## Architektura pipeline

```
┌───────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                         run-all Pipeline (11 kroków)                                       │
├───────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                            │
│  [0a] scrape episodes   →  [1] transcode  →  [2] transcribe  →  [3] detect scenes                        │
│       (Qwen + crawl4ai)      (NVENC)           (Whisper)          (TransNetV2)                            │
│                                                                                                            │
│  [0b] scrape characters →  [0c] download references                                                       │
│       (Qwen + crawl4ai)       (DuckDuckGo + InsightFace)                                                  │
│                                                                                                            │
│  [4] export frames  →  [5] image hashing  →  [6] embeddings  →  [7] detect characters                    │
│      (480p JPG)         (perceptual hash)      (Qwen2-VL)         (InsightFace)                           │
│                                                                                                            │
│  [8] generate elastic docs  →  [9] index                                                                  │
│      (JSON merging)             (Elasticsearch)                                                            │
│                                                                                                            │
│  Całkowicie SEKWENCYJNE przetwarzanie (pipeline + pliki w każdej fazie)                                   │
│  Optymalizacja dla jednego GPU bez strat wydajności                                                       │
│                                                                                                            │
└───────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Czas przetwarzania (RTX 3090 + 64GB RAM)

| Faza                           | Czas (45 min odcinek) |
|--------------------------------|----------------------|
| Transcode (NVENC)              | ~2 min |
| Transcribe (Whisper)           | ~5 min |
| Scene detection (TransNetV2)   | ~3 min |
| Export frames (480p)           | ~2 min |
| Image hashing                  | ~1 min |
| **Embeddings (batch_size=28)** | **~5-7 min** |
| Character detection            | ~2 min |
| Generate elastic docs          | ~1 min |
| Index (Elasticsearch)          | ~2 min |
| **Łącznie**                    | **~23-25 min** |

**Throughput:** ~2-3 odcinki (45 min każdy) na godzinę przetwarzania.

**Jednorazowo (na całą serię):**
- Scrape episodes: ~1-2 min (wszystkie sezony)
- Scrape characters: ~1-2 min (wszystkie postacie)
- Download references: ~5-10 min (zależnie od liczby postaci)

---

## Struktura projektu

```
preprocessor/
├── cli/                     # Interfejs CLI (modularny)
│   ├── commands/           # Komendy CLI (16 modułów)
│   ├── options/            # Wspólne opcje CLI
│   ├── pipeline/           # Orchestrator pipeline
│   └── utils.py
├── config/                  # Konfiguracja aplikacji
├── core/                    # BaseProcessor, StateManager
├── video/                   # Przetwarzanie wideo
│   ├── transcoder.py       # FFmpeg + NVENC
│   ├── scene_detector.py   # TransNetV2
│   └── frame_exporter.py   # Eksport klatek (480p)
├── transcription/           # Transkrypcja audio
│   ├── engines/            # Whisper, ElevenLabs
│   ├── generators/         # JSON, SRT, TXT
│   └── processors/         # Normalizacja audio
├── scraping/                # Scrapowanie metadanych
│   ├── episode_scraper.py  # crawl4ai + Ollama (odcinki)
│   ├── character_scraper.py # crawl4ai + Ollama (postacie)
│   └── crawl4ai.py
├── characters/              # Wykrywanie postaci
│   ├── detector.py         # InsightFace face recognition
│   └── reference_downloader.py # DuckDuckGo image search
├── hashing/                 # Perceptual hashing
│   └── image_hash_processor.py
├── embeddings/              # Generowanie embeddingów
│   ├── generator.py        # Qwen2-VL
│   └── strategies/         # Frame selection
├── indexing/                # Elasticsearch
│   ├── elastic_document_generator.py
│   └── indexer.py
├── search/                  # elastic_manager
├── providers/               # LLM (Ollama)
├── input_data/              # [volume] Dane wejściowe (read-only)
├── output_data/             # [volume] Dane wygenerowane
└── docker-compose.yml
```

### Wolumeny Docker

| Host | Container | Tryb |
|------|-----------|------|
| `input_data/` | `/input_data` | read-only |
| `output_data/` | `/app/output_data` | read-write |
| `ml_models` (named) | `/models` | persistent (~25GB) |

---

## Komendy CLI

Wszystkie komendy: `../run-preprocessor.sh <komenda> [args]`

Pomoc: `../run-preprocessor.sh --help`

### run-all

Pełny pipeline ze wszystkimi krokami (11 kroków).

```bash
# Z automatycznym scrapingiem metadanych (odcinki + postacie)
../run-preprocessor.sh run-all /input_data/videos \
  --scrape-urls https://ranczo.fandom.com/wiki/Seria_I \
  --character-urls https://ranczo.fandom.com/wiki/Lista_postaci \
  --series-name ranczo

# Z istniejącym episodes.json
../run-preprocessor.sh run-all /input_data/videos \
  --episodes-info-json /input_data/episodes.json \
  --series-name ranczo

# Pominięcie wybranych kroków
../run-preprocessor.sh run-all /input_data/videos \
  --episodes-info-json /input_data/episodes.json \
  --series-name ranczo \
  --skip-transcode \
  --skip-frame-export
```

### scrape-episodes

Batch scraping metadanych odcinków.

**Flow:** URLe → crawl4ai (markdown) → Qwen2.5-Coder-7B (128K context) → JSON

```bash
../run-preprocessor.sh scrape-episodes \
  --urls https://ranczo.fandom.com/wiki/Seria_I \
  --urls https://ranczo.fandom.com/wiki/Seria_II \
  --output-file /input_data/episodes.json
```

**Uwaga:** Scraping postaci (`--character-urls`) i pobieranie ich referencyjnych zdjęć dzieje się automatycznie w ramach `run-all` pipeline. Brak osobnych komend CLI dla tych operacji.

### transcode

Transkodowanie wideo (Jellyfin FFmpeg 7 + NVENC).

```bash
../run-preprocessor.sh transcode /input_data/videos \
  --episodes-info-json /input_data/episodes.json \
  --resolution 1080p
```

### transcribe

Transkrypcja audio (Whisper large-v3-turbo).

```bash
../run-preprocessor.sh transcribe /input_data/videos \
  --episodes-info-json /input_data/episodes.json \
  --name ranczo \
  --model large-v3-turbo
```

### transcribe-elevenlabs

Transkrypcja przez ElevenLabs API (płatne, speaker diarization).

```bash
export ELEVEN_API_KEY=your_key
../run-preprocessor.sh transcribe-elevenlabs /input_data/videos \
  --name ranczo \
  --episodes-info-json /input_data/episodes.json
```

### import-transcriptions

Import istniejących transkrypcji.

```bash
../run-preprocessor.sh import-transcriptions \
  --source-dir /input_data/11labs_output \
  --name ranczo \
  --format-type 11labs_segmented
```

### detect-scenes

Detekcja scen (TransNetV2).

```bash
../run-preprocessor.sh detect-scenes /input_data/videos \
  --threshold 0.5
```

### export-frames

Eksport klatek wideo (480p) na podstawie strategii keyframe.

```bash
../run-preprocessor.sh export-frames /input_data/transcoded_videos \
  --episodes-info-json /input_data/episodes.json \
  --scene-timestamps-dir /app/output_data/scene_timestamps \
  --name ranczo \
  --frame-height 480
```

### image-hashing

Generowanie perceptual hashes dla wyeksportowanych klatek.

```bash
../run-preprocessor.sh image-hashing \
  --frames-dir /app/output_data/frames \
  --episodes-info-json /input_data/episodes.json \
  --name ranczo \
  --batch-size 28
```

### generate-embeddings

Generowanie embeddingów tekst+wideo (gme-Qwen2-VL-2B).

```bash
# Scene-based (domyślnie)
../run-preprocessor.sh generate-embeddings \
  --transcription-jsons /app/output_data/transcriptions \
  --videos /input_data/videos \
  --scene-timestamps-dir /app/output_data/scene_timestamps \
  --batch-size 28

# Keyframe-based
../run-preprocessor.sh generate-embeddings \
  --transcription-jsons /app/output_data/transcriptions \
  --videos /input_data/videos \
  --keyframe-strategy keyframes \
  --keyframe-interval 1
```

### generate-elastic-documents

Generowanie dokumentów Elasticsearch (łączenie transkrypcji, embeddingów, scen).

```bash
../run-preprocessor.sh generate-elastic-documents \
  --transcription-jsons /app/output_data/transcriptions \
  --embeddings-dir /app/output_data/embeddings \
  --scene-timestamps-dir /app/output_data/scene_timestamps \
  --name ranczo \
  --output-dir /app/output_data/elastic_documents
```

### index

Indeksowanie w Elasticsearch.

```bash
# Nowy indeks
../run-preprocessor.sh index \
  --name ranczo \
  --transcription-jsons /app/output_data/transcriptions

# Append do istniejącego
../run-preprocessor.sh index \
  --name ranczo \
  --transcription-jsons /app/output_data/transcriptions \
  --append
```

### convert-elastic

Migracja legacy indeksu (jednorazowa).

```bash
../run-preprocessor.sh convert-elastic \
  --index-name ranczo \
  --dry-run
```

---

## Scenariusze użycia

### 1. Pełny pipeline od zera (11 kroków)

```bash
cd preprocessor
mkdir -p input_data/videos output_data
cp /ścieżka/do/*.mp4 input_data/videos/

docker-compose build

../run-preprocessor.sh run-all /input_data/videos \
  --scrape-urls https://ranczo.fandom.com/wiki/Seria_I \
  --character-urls https://ranczo.fandom.com/wiki/Lista_postaci \
  --series-name ranczo
```

### 2. Z gotową transkrypcją i transkodowaniem

```bash
../run-preprocessor.sh detect-scenes /input_data/videos

../run-preprocessor.sh export-frames /input_data/videos \
  --episodes-info-json /input_data/episodes.json \
  --scene-timestamps-dir /app/output_data/scene_timestamps \
  --name ranczo

../run-preprocessor.sh image-hashing \
  --frames-dir /app/output_data/frames \
  --episodes-info-json /input_data/episodes.json \
  --name ranczo

../run-preprocessor.sh generate-embeddings \
  --transcription-jsons /app/output_data/transcriptions \
  --videos /input_data/videos \
  --scene-timestamps-dir /app/output_data/scene_timestamps

../run-preprocessor.sh generate-elastic-documents \
  --transcription-jsons /app/output_data/transcriptions \
  --embeddings-dir /app/output_data/embeddings \
  --name ranczo

../run-preprocessor.sh index --name ranczo \
  --transcription-jsons /app/output_data/transcriptions
```

### 3. Z gotowym episodes.json

```bash
../run-preprocessor.sh run-all /input_data/videos \
  --episodes-info-json /input_data/episodes.json \
  --series-name ranczo
```

### 4. Pominięcie niektórych kroków (skip flags)

```bash
../run-preprocessor.sh run-all /input_data/videos \
  --episodes-info-json /input_data/episodes.json \
  --series-name ranczo \
  --skip-transcode \
  --skip-transcribe \
  --skip-frame-export
```

### 5. Tylko transkrypcja (bez embeddings i wykrywania postaci)

```bash
../run-preprocessor.sh transcode /input_data/videos \
  --episodes-info-json /input_data/episodes.json

../run-preprocessor.sh transcribe /input_data/videos \
  --episodes-info-json /input_data/episodes.json \
  --name ranczo
```

---

## Technologie

| Komponent | Technologia | Opis |
|-----------|-------------|------|
| Transkodowanie | Jellyfin FFmpeg 7 + NVENC | GPU encoding h264_nvenc |
| Transkrypcja | Whisper large-v3-turbo | CTranslate2 GPU (~3GB) |
| Detekcja scen | TransNetV2 | PyTorch GPU (~1GB) |
| Eksport klatek | FFmpeg | 480p JPG extraction |
| Perceptual hashing | ImageHash | pHash algorithm |
| Embeddingi | gme-Qwen2-VL-2B-Instruct | float16 (~5GB) |
| Face recognition | InsightFace (buffalo_l) | ArcFace embeddings (~1GB) |
| Image search | DuckDuckGo (DDGS) | Reference images download |
| LLM scraping | Qwen2.5-Coder-7B-Instruct | 8-bit, 128K context (~8GB) |
| Video decoding | Decord | GPU (5-10x szybsze niż OpenCV) |
| Search | Elasticsearch | Full-text + vector indexing |
| Web scraping | crawl4ai | Markdown extraction |

**Cache modeli:** ~30GB w wolumenie `ranchbot-ai-models` (persistent)

---

## Format plików wideo

### Wspierane formaty

Pipeline wspiera wszystkie popularne formaty wideo (transkoder konwertuje wszystko do MP4):

**Wejście:** `.mp4`, `.avi`, `.mkv`, `.mov`, `.flv`, `.wmv`, `.webm`
**Wyjście:** `.mp4` (h264_nvenc, AAC audio)

### Nazewnictwo plików

Pipeline ekstraktuje kod odcinka z nazwy pliku:

| Format | Przykład | Uwagi |
|--------|----------|-------|
| `S01E01` | Ranczo S01E12.mp4 | Zalecane |
| `s01e12` | s01e12.mp4 | Case-insensitive |
| `E012` | E012.mp4 | Wymaga episodes.json |

**Przykład transformacji:**
- Input: `Sezon 1/Ranczo S01E12.F012.Netflix.mkv`
- Output: `ranczo_S01E12.mp4`

Pliki bez rozpoznawalnego kodu będą pominięte.

---

## episodes.json

Automatycznie generowany przez LLM z wielu URLi naraz.

**Proces:**
1. Podajesz 1-10 URLi
2. crawl4ai pobiera wszystkie strony → markdown
3. Qwen2.5-Coder-7B (128K context) → JSON

**Format:**

```json
{
  "sources": [
    "https://ranczo.fandom.com/wiki/Seria_I",
    "https://filmweb.pl/serial/Ranczo-2006"
  ],
  "seasons": [
    {
      "season_number": 1,
      "episodes": [
        {
          "episode_number": 1,
          "title": "Pilot",
          "premiere_date": "2006-03-05",
          "viewership": 4500000
        }
      ]
    }
  ]
}
```

---

## characters.json

Automatycznie generowany przez LLM przy użyciu `--character-urls`.

**Proces:**
1. Podajesz URLe z listami postaci
2. crawl4ai pobiera strony → markdown
3. Qwen2.5-Coder-7B (128K context) → JSON z imionami i nazwiskami
4. DuckDuckGo wyszukuje referencyjne zdjęcia (automatycznie)
5. InsightFace weryfikuje twarze na zdjęciach (1 twarz = OK)

**Format:**

```json
{
  "sources": [
    "https://ranczo.fandom.com/wiki/Lista_postaci"
  ],
  "characters": [
    {
      "name": "Lucy Wilska",
      "role": "główna"
    },
    {
      "name": "Wicek Wilski",
      "role": "główna"
    }
  ]
}
```

**Referencyjne zdjęcia:** Zapisywane w `output_data/characters/{nazwa_postaci}/00.jpg`, `01.jpg`, ...

---

## Instalacja

### Wymagania software

- Docker 20.10+
- Docker Compose 1.29+
- NVIDIA Container Toolkit (WYMAGANE)
- NVIDIA Driver 525+ (CUDA 12.1)
- Linux (Ubuntu 22.04) lub WSL2

### Instalacja NVIDIA Container Toolkit

```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# Weryfikacja
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

---

## Monitoring

```bash
# Logi w czasie rzeczywistym
docker logs ranchbot-preprocessing-app -f

# Wejście do kontenera
docker-compose -f preprocessor/docker-compose.yml run --rm preprocessor bash

# Sprawdzenie GPU
nvidia-smi

# Sprawdzenie NVENC
ffmpeg -encoders | grep nvenc
```

---

## Troubleshooting

### Sprawdzenie GPU i NVENC

```bash
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
docker-compose -f preprocessor/docker-compose.yml run --rm preprocessor ffmpeg -encoders | grep nvenc
```

### Brak miejsca na dysku

```bash
docker system prune -a
docker volume prune

# Uwaga: re-download przy następnym uruchomieniu
docker volume rm ranchbot-ai-models
```

### Out of memory (CUDA OOM)

```bash
# Aplikacja domyślnie używa batch_size=28 (RTX 3090)
# Jeśli masz inną kartę, musisz dostosować ręcznie:
../run-preprocessor.sh generate-embeddings --batch-size 14  # dla ~16GB VRAM
../run-preprocessor.sh generate-embeddings --batch-size 7   # dla ~12GB VRAM
```

### Kontener się crashuje

```bash
docker logs ranchbot-preprocessing-app --tail 200
docker-compose -f preprocessor/docker-compose.yml run --rm preprocessor bash
```

---

## Wydajność (RTX 3090 + 64GB RAM)

**Konfiguracja testowa (jedyna wspierana):**

| Metryka | Wartość                         |
|---------|---------------------------------|
| **GPU** | **RTX 3090 24GB**               |
| **RAM** | **64GB**                        |
| **Throughput** | **~3-4 odcinki/godzinę**        |
| **Batch size** | **28 (default)**                |
| **Peak VRAM** | **~12GB (~50% wykorzystania)**  |
| **Peak RAM** | **~32GB (~50% wykorzystania)**  |
| **Przetwarzanie** | **Sekwencyjne (1 plik na raz)** |

Pipeline sekwencyjny (jeden plik na raz w każdej fazie) maksymalnie wykorzystuje GPU bez marnotrawstwa zasobów na równoległość.
# Video Preprocessing Pipeline

Aplikacja Docker do przetwarzania wideo z akceleracją GPU (NVIDIA): transkodowanie, transkrypcja (Whisper/ElevenLabs), detekcja scen, generowanie embeddingów i indeksowanie w Elasticsearch.

## Szybki start

```bash
cd preprocessor
mkdir -p input_data/videos output_data
cp /twoje/wideo/*.mp4 input_data/videos/

docker-compose build

../run-preprocessor.sh run-all /input_data/videos \
  --scrape-urls https://ranczo.fandom.com/wiki/Seria_I \
  --name ranczo

docker logs ranchbot-preprocessing-app -f
```

**Wymagania:** NVIDIA GPU RTX 3090 (24GB VRAM), 64GB RAM, Docker + NVIDIA Container Toolkit

**UWAGA:** Aplikacja działa TYLKO na Docker + GPU NVIDIA. Nie ma fallbacku na CPU.

## Struktura projektu

```
preprocessor/
├── config/                  # Konfiguracja aplikacji
├── core/                    # Podstawowe komponenty (state_manager)
├── video/                   # Przetwarzanie wideo
│   ├── transcoder.py       # Transkodowanie (FFmpeg + NVENC)
│   └── scene_detector.py   # Detekcja scen (TransNetV2)
├── transcription/           # Transkrypcja audio
│   ├── engines/            # Silniki transkrypcji (Whisper, ElevenLabs)
│   ├── generators/         # Generatory formatów wyjściowych (JSON, SRT, TXT)
│   ├── processors/         # Procesory audio (normalizacja)
│   ├── generator.py        # Generator transkrypcji (Whisper)
│   ├── elevenlabs.py       # Transkrypcja przez ElevenLabs API
│   └── importer.py         # Import istniejących transkrypcji
├── scraping/                # Scrapowanie metadanych
│   ├── episode_scraper.py  # Scraper odcinków (crawl4ai + Ollama)
│   ├── crawl4ai.py         # Crawler stron WWW
│   └── clipboard.py        # Scraper ze schowka
├── embeddings/              # Generowanie embeddingów
│   └── generator.py        # Generator embeddingów (Qwen2-VL)
├── indexing/                # Indeksowanie
│   └── elasticsearch.py    # Indeksowanie w Elasticsearch
├── providers/               # Providery zewnętrznych serwisów
│   └── llm.py              # Provider LLM (Ollama)
├── utils/                   # Narzędzia pomocnicze
├── scripts/                 # Skrypty pomocnicze (download_models)
├── prompts/                 # Prompty LLM
├── legacy/                  # Konwersje legacy
├── input_data/              # Dane wejściowe (tylko odczyt)
│   └── videos/              # Pliki wideo (*.mp4)
├── output_data/             # Dane wygenerowane
│   ├── transcoded_videos/   # Wideo H.264 z keyframe'ami
│   ├── transcriptions/      # Transkrypcje audio (JSON, SRT, TXT)
│   ├── embeddings/          # Embeddingi tekst+wideo (NPZ)
│   ├── scene_timestamps/    # Timestampy scen (JSON)
│   └── scraped_pages/       # Zescrapowane strony (markdown)
├── docker-compose.yml
├── Dockerfile
└── README.md
```

**Wolumeny Docker:**
* `input_data/` → `/input_data` (read-only)
* `output_data/` → `/app/output_data` (read-write)
* `ml_models` → `/models` (~50GB, persistent)

## Dostępne komendy

Wszystkie komendy wywołuj przez: `../run-preprocessor.sh <komenda> [args]`

Pomoc: `../run-preprocessor.sh --help` lub `../run-preprocessor.sh <komenda> --help`

### run-all

Pełny pipeline: [scrape] → transcode → transcribe → scenes → embeddings → index

```bash
# Z automatycznym scrapingiem metadanych
../run-preprocessor.sh run-all /input_data/videos \
  --scrape-urls https://ranczo.fandom.com/wiki/Seria_I \
  --name ranczo

# Z istniejącym episodes.json
../run-preprocessor.sh run-all /input_data/videos \
  --episodes-info-json /input_data/episodes.json \
  --name ranczo
```

**Czas przetwarzania:** ~20min na 45-minutowy odcinek (RTX 3090)

**Równoległość:** Pipeline przetwarza wiele odcinków równolegle w ramach każdej fazy. Fazy wykonują się sekwencyjnie:
1. Transcode (wiele odcinków równolegle) → czeka aż wszystkie skończą
2. Transcribe (wiele odcinków równolegle) → czeka aż wszystkie skończą
3. Scenes (wiele odcinków równolegle) → czeka aż wszystkie skończą
4. Embeddings → Index

### scrape-episodes

Scraping metadanych odcinków z wielu stron WWW naraz (batch processing)

**Flow:** Wszystkie URLe → crawl4ai (markdown) → Ollama qwen3-coder:30b (50k context) → JSON

```bash
# Jeden URL (może zawierać wiele sezonów)
../run-preprocessor.sh scrape-episodes \
  --urls https://filmweb.pl/serial/Ranczo-2006 \
  --output-file /input_data/episodes.json

# Wiele URLi naraz (każdy może mieć jeden lub więcej sezonów)
../run-preprocessor.sh scrape-episodes \
  --urls https://ranczo.fandom.com/wiki/Seria_I \
  --urls https://ranczo.fandom.com/wiki/Seria_II \
  --urls https://filmweb.pl/serial/Ranczo-2006 \
  --output-file /input_data/episodes.json
```

**Batch processing:** Wszystkie strony są pobierane (crawl4ai), potem cały markdown trafia jednym requestem do Ollama (qwen3-coder:30b, 50k context), który zwraca kompletny JSON ze wszystkimi sezonami.

### transcode

Transkodowanie wideo (Jellyfin FFmpeg 7 + NVENC GPU, h264_nvenc)

```bash
../run-preprocessor.sh transcode /input_data/videos \
  --episodes-info-json /input_data/episodes.json \
  --resolution 1080p
```

### transcribe

Transkrypcja audio (Whisper large-v3-turbo, GPU)

```bash
../run-preprocessor.sh transcribe /input_data/videos \
  --episodes-info-json /input_data/episodes.json \
  --name ranczo \
  --model large-v3-turbo
```

### transcribe-elevenlabs

Transkrypcja przez ElevenLabs API (płatne, speaker diarization)

```bash
export ELEVEN_API_KEY=your_key
../run-preprocessor.sh transcribe-elevenlabs /input_data/videos \
  --name ranczo \
  --episodes-info-json /input_data/episodes.json
```

### import-transcriptions

Import istniejących transkrypcji (format 11labs)

```bash
../run-preprocessor.sh import-transcriptions \
  --source-dir /input_data/11labs_output \
  --name ranczo \
  --episodes-info-json /input_data/episodes.json \
  --format-type 11labs_segmented
```

### detect-scenes

Detekcja scen (TransNetV2, GPU)

```bash
../run-preprocessor.sh detect-scenes /input_data/videos \
  --threshold 0.5
```

### generate-embeddings

Generowanie embeddingów tekst+wideo (Qwen2-VL-7B, GPU batch inference)

```bash
# Scene-based (domyślnie): 3 klatki na scenę
../run-preprocessor.sh generate-embeddings \
  --transcription-jsons /app/output_data/transcriptions \
  --videos /input_data/videos \
  --scene-timestamps-dir /app/output_data/scene_timestamps \
  --batch-size 24

# Keyframe-based: co 5s
../run-preprocessor.sh generate-embeddings \
  --transcription-jsons /app/output_data/transcriptions \
  --videos /input_data/videos \
  --keyframe-strategy keyframes \
  --keyframe-interval 1
```

### index

Indeksowanie w Elasticsearch

```bash
../run-preprocessor.sh index \
  --name ranczo \
  --transcription-jsons /app/output_data/transcriptions

# Z append (bez usuwania istniejącego indeksu)
../run-preprocessor.sh index \
  --name ranczo \
  --transcription-jsons /app/output_data/transcriptions \
  --append
```

### convert-elastic

Konwersja legacy Elasticsearch index (one-time migration)

```bash
../run-preprocessor.sh convert-elastic \
  --index-name ranczo \
  --dry-run
```

## Technologie

* **Jellyfin FFmpeg 7** - Transkodowanie z NVENC GPU support
* **Whisper large-v3-turbo** - Transkrypcja audio (CTranslate2 GPU, ~3GB)
* **TransNetV2** - Detekcja scen (PyTorch GPU, ~1GB)
* **Qwen2-VL-7B** (gme-Qwen2-VL-7B-Instruct) - Multimodal embeddings (~15GB)
* **Ollama qwen3-coder:30b-a3b-q4_K_M** - LLM do scrapingu (50k context, ~20GB)
* **Decord** - GPU video decoding (5-10x szybsze niż OpenCV)
* **Elasticsearch** - Full-text search indexing
* **crawl4ai** - Web scraping (markdown extraction)

**Modele cache:** ~50GB w wolumenie `ranchbot-ai-models` (persistent)

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

## Wymagania systemowe

### Hardware (WYMAGANE, bez fallbacku na CPU)
* **GPU:** NVIDIA RTX 3090 (24GB VRAM) - domyślna konfiguracja
* **RAM:** 64GB (zalecane dla pełnego pipeline)
* **Dysk:** ~100GB wolnego miejsca (50GB modele + 50GB output)

### Software
* Docker 20.10+
* Docker Compose 1.29+
* NVIDIA Container Toolkit (WYMAGANE)
* NVIDIA Driver 525+ (CUDA 12.1 support)
* Linux (Ubuntu 22.04) lub WSL2

**UWAGA:** Cała aplikacja wymaga GPU NVIDIA. Nie ma trybu CPU - wszystkie operacje (transcode NVENC, Whisper, TransNetV2, embeddings) używają GPU.

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

## Format plików wideo

Pipeline ekstraktuje kod odcinka z nazwy pliku, ignorując strukturę folderów i resztę nazwy:

**Wspierane formaty:**
* `S01E01` - Sezon 1, Odcinek 1 (zalecane)
* `s01e12` - Case-insensitive
* `E012` - Absolutny numer odcinka (wymaga episodes.json)

**Przykład:**
* Input: `Sezon 1/Ranczo S01E12.F012.Netflix.mp4`
* Output: `ranczo_S01E12.mp4`

Pliki bez rozpoznawalnego kodu będą pominięte.

## episodes.json

**Automatycznie generowany OUTPUT** z wielu stron WWW naraz przez Ollama.

**Proces generowania:**
1. Podajesz 1-10 URLi (każdy może mieć jeden lub więcej sezonów)
2. crawl4ai pobiera wszystkie strony → markdown
3. Wszystkie markdown naraz trafiają do Ollama (qwen3-coder:30b-a3b-q4_K_M, 50k context)
4. Ollama zwraca kompletny JSON ze wszystkimi sezonami

**Format OUTPUT:**

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

**Przykład użycia:**

```bash
# 10 URLi naraz → crawl4ai → markdown → Ollama (1 request) → JSON
../run-preprocessor.sh scrape-episodes \
  --urls https://ranczo.fandom.com/wiki/Seria_I \
  --urls https://ranczo.fandom.com/wiki/Seria_II \
  --urls https://ranczo.fandom.com/wiki/Seria_III \
  --output-file /input_data/episodes.json
```

Lub użyj `run-all` z `--scrape-urls` - episodes.json zostanie utworzony automatycznie w pierwszym kroku pipeline (używa Ollama).

## Troubleshooting

### Sprawdzenie GPU i NVENC

```bash
# Sprawdź NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi

# Sprawdź FFmpeg NVENC (powinno być widoczne)
docker-compose -f preprocessor/docker-compose.yml run --rm preprocessor ffmpeg -encoders | grep nvenc
```

### Brak miejsca na dysku

```bash
# Czyszczenie Docker
docker system prune -a
docker volume prune

# Usunięcie cache modeli (uwaga: re-download przy następnym uruchomieniu)
docker volume rm ranchbot-ai-models
```

### Out of memory (CUDA OOM)

```bash
# Zmniejsz batch_size dla embeddings (domyślnie 24 dla RTX 3090)
../run-preprocessor.sh generate-embeddings --batch-size 16
```

### Kontener się crashuje

```bash
# Sprawdź logi
docker logs ranchbot-preprocessing-app --tail 200

# Uruchom interaktywny bash
docker-compose -f preprocessor/docker-compose.yml run --rm preprocessor bash
```

## Wydajność (RTX 3090, 64GB RAM)

**Pipeline `run-all`:** ~20 minut na 45-minutowy odcinek

**Rozkład czasu (pojedynczy odcinek):**
* Transcode (NVENC GPU): ~2 min
* Transcribe (Whisper GPU): ~5 min
* Scene detection (TransNetV2 GPU): ~3 min
* Embeddings (Qwen2-VL GPU batch): ~8 min
* Index (Elasticsearch): ~2 min

**Równoległość:** Przy przetwarzaniu wielu odcinków, każda faza przetwarza wiele odcinków równolegle (ograniczone GPU VRAM). Fazy wykonują się sekwencyjnie - jedna faza musi zakończyć wszystkie odcinki przed rozpoczęciem następnej.

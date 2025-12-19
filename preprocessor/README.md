# Video Preprocessing Pipeline - Docker-Only Application

A video processing application **designed exclusively for execution in Docker** with GPU acceleration (NVIDIA). Comprehensive pipeline: transcoding, transcription (Whisper/ElevenLabs), scene detection, embedding generation, and indexing in Elasticsearch.

---

## 🚀 Quick Start

```bash
# 1. Prepare environment
cd preprocessor
mkdir -p input_data/videos output_data
cp /your/video/*.mp4 input_data/videos/

# 2. Build Docker image
docker-compose build

# 3. Run full pipeline (scraper generates episodes.json automatically)
../run-preprocessor.sh run-all /input_data/videos \
  --scrape-urls https://ranczo.fandom.com/wiki/Seria_I \
  --name ranczo

# 4. Monitor progress
docker logs ranchbot-preprocessing-app -f

```

**Requirements:** NVIDIA GPU (RTX 3090+), 64GB RAM, Docker + NVIDIA Container Toolkit

---

## 📁 Project Structure

```
preprocessor/
├── input_data/              # 👈 Your input data (mounted read-only)
│   └── videos/              #    Raw video files (*.mp4)
├── output_data/             # 👈 Generated data (automatic)
│   ├── transcoded_videos/   #    Processed video (H.264, GOP keyframes)
│   ├── transcriptions/      #    Audio transcriptions (JSON)
│   ├── embeddings/          #    Text+video embeddings (NPZ)
│   └── scene_timestamps/    #    Scene timestamps (JSON)
├── docker-compose.yml       # Docker configuration
├── Dockerfile               # Image definition
└── README.md                # This file

```

**Docker Volumes:**

* `input_data/` → `/input_data` (read-only)
* `output_data/` → `/app/output_data` (read-write)
* `ml_models` → `/models` (persistent volume, ~50GB)

---

## 🐳 Why Docker Only?

✅ **Zero configuration** - CUDA 12.1, cuDNN, PyTorch, FFmpeg NVENC pre-configured

✅ **Persistent cache** - ML models downloaded once, cached in volume (~50GB)

✅ **GPU support** - NVIDIA runtime automatically handles NVENC and CUDA

✅ **Reproducibility** - Identical environment on every machine

 ✅ **Isolation** - No conflicts with host system

✅ **Logging** - All logs visible via `docker logs`


---

## 📋 Requirements

### Hardware

* **NVIDIA GPU** - RTX 3090 / RTX 4090 or better (24GB VRAM recommended)
* **RAM** - 64GB (recommended), minimum 32GB
* **Disk** - ~100GB free space (50GB ML models + 50GB output)
* **CPU** - Multi-core (8+ cores recommended)

### Software

* **Docker** - version 20.10+
* **Docker Compose** - version 1.29+
* **NVIDIA Container Toolkit**
* **NVIDIA Driver** - version 525+ (CUDA 12.1 support)
* **OS** - Linux (Ubuntu 22.04) or WSL2 (Windows)

### NVIDIA Container Toolkit Installation

```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# Verification
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi

```

---

## 🎬 Usage

### Full Pipeline (All steps automatically)

**Option 1: With URL scraping (recommended - generates episodes.json automatically)**

```bash
../run-preprocessor.sh run-all /input_data/videos \
  --scrape-urls https://ranczo.fandom.com/wiki/Seria_I \
  --name ranczo

```

**Option 2: With existing episodes.json**

```bash
../run-preprocessor.sh run-all /input_data/videos \
  --episodes-info-json /input_data/episodes.json \
  --name ranczo

```

**The pipeline executes 5-6 steps:**

0. **Scrape** (optional) - Extract episode metadata from URLs → generates episodes.json
1. **Transcode** - Video conversion to H.264 with keyframes (GPU NVENC)
2. **Transcribe** - Audio transcription (Whisper large-v3-turbo, GPU)
3. **Detect-scenes** - Scene detection (TransNetV2, GPU)
4. **Generate-embeddings** - Text+video embeddings (Qwen2-VL-7B, GPU batch)
5. **Index** - Indexing in Elasticsearch

**Processing time:** ~20-25min for a 45-minute episode (RTX 3090, including scraping)

### Single Steps (Manual control)

```bash
# Step 1: Video transcoding
../run-preprocessor.sh transcode /input_data/videos \
  --episodes-info-json /input_data/episodes.json \
  --resolution 1080p \
  --codec h264_nvenc

# Step 2: Audio transcription
../run-preprocessor.sh transcribe /input_data/videos \
  --episodes-info-json /input_data/episodes.json \
  --name ranczo \
  --model large-v3-turbo \
  --device cuda

# Step 3: Scene detection
../run-preprocessor.sh detect-scenes /input_data/videos \
  --threshold 0.5 \
  --device cuda

# Step 4: Generate embeddings
../run-preprocessor.sh generate-embeddings \
  --transcription-jsons /app/output_data/transcriptions \
  --videos /input_data/videos \
  --scene-timestamps-dir /app/output_data/scene_timestamps \
  --batch-size 24 \
  --device cuda

# Step 5: Indexing in Elasticsearch
../run-preprocessor.sh index \
  --name ranczo \
  --transcription-jsons /app/output_data/transcriptions

```

### Alternative Transcription Methods

**ElevenLabs API** (paid, better quality, diarization):

```bash
../run-preprocessor.sh transcribe-elevenlabs /input_data/videos \
  --name ranczo \
  --episodes-info-json /input_data/episodes.json \
  --api-key $ELEVEN_API_KEY

```

**Import existing transcriptions** (11labs format):

```bash
../run-preprocessor.sh import-transcriptions \
  --source-dir /input_data/11labs_output \
  --name ranczo \
  --episodes-info-json /input_data/episodes.json \
  --format-type 11labs_segmented

```

### Scraping Episode Metadata

```bash
../run-preprocessor.sh scrape-episodes \
  --urls https://filmweb.pl/serial/Ranczo-2006 \
  --output-file /input_data/episodes.json \
  --llm-provider ollama

```

---

## 📊 Monitoring and Debugging

### Tracking Logs in Real-Time

```bash
# Variant 1: docker-compose logs
docker-compose logs -f preprocessor

# Variant 2: docker logs (direct)
docker logs ranchbot-preprocessing-app -f

# Only last 100 lines
docker logs ranchbot-preprocessing-app --tail 100 -f

```

### Log Format

All logs are sent to stderr and visible in `docker logs`:

* `[ENTRYPOINT]` - Initialization, Ollama, ML models
* `[VideoTranscoder]` - Video transcoding, FFmpeg
* `[TranscriptionGenerator]` - Whisper transcription
* `[SceneDetector]` - TransNetV2 scene detection
* `[EmbeddingGenerator]` - Qwen2-VL embedding generation
* `[ElasticSearchIndexer]` - Indexing

### Entering the Container (Debugging)

```bash
# Bash session inside container
docker-compose run --rm preprocessor bash

# Check GPU
nvidia-smi

# Check NVENC
ffmpeg -encoders | grep nvenc

# Check ML models
ls -lah /models/

# Run commands manually
python -m preprocessor --help

```

### Volume Management (ML models cache)

```bash
# Check models cache size
docker volume inspect ranchbot-ai-models

# Backup models
docker run --rm \
  -v ranchbot-ai-models:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/models-backup.tar.gz /data

# Clear cache (frees ~50GB, requires re-download)
docker volume rm ranchbot-ai-models

```

---

## 💡 Help for Commands

```bash
# Global help
../run-preprocessor.sh --help

# Help for specific command
../run-preprocessor.sh transcode --help
../run-preprocessor.sh transcribe --help
../run-preprocessor.sh generate-embeddings --help

```

---

## 📁 Episode Metadata (episodes.json)

**This file is OUTPUT generated by the scraper** (Step 0 of pipeline). It contains episode metadata extracted from URLs.

**Example episodes.json structure:**

```json
{
  "seasons": [
    {
      "season_number": 1,
      "episodes": [
        {
          "episode_number": 1,
          "title": "Pilot",
          "premiere_date": "2006-03-05",
          "viewership": 4500000
        },
        {
          "episode_number": 2,
          "title": "Second episode",
          "premiere_date": "2006-03-12",
          "viewership": 4600000
        }
      ]
    }
  ]
}

```

**To generate this file, use:**

```bash
../run-preprocessor.sh scrape-episodes \
  --urls https://filmweb.pl/serial/Ranczo-2006 \
  --output-file /input_data/episodes.json

# Or use run-all with --scrape-urls (automatic)
../run-preprocessor.sh run-all /input_data/videos \
  --scrape-urls https://ranczo.fandom.com/wiki/Seria_I \
  --name ranczo

```

**Video file naming convention:**

**IMPORTANT:** The pipeline extracts ONLY the episode code from filenames, ignoring:
- ✅ Folder structure (searches recursively in all subfolders)
- ✅ Rest of filename (e.g., `Ranczo S01E12.F012.Netflix.mp4` → extracts `S01E12`)
- ✅ File location (can be in any subfolder like `Sezon 1/`, `Season 1/`, etc.)

**Supported formats:**
* `S01E01` → Season 1, Episode 1 (recommended)
* `s01e12` → Case-insensitive
* `E012` → Absolute episode number (requires episodes.json mapping)

**Output normalization:**
All output files are automatically renamed using `--name` parameter:
* Input: `Sezon 1/Ranczo S01E12.F012.Netflix.mp4`
* Output: `ranczo_S01E12.mp4` (in `Sezon 1/` subfolder)

Files without recognizable episode codes will be skipped.

---

## 🔧 Technical Details

### Pipeline Architecture

```
Video (.mp4)
  → FFmpeg NVENC (GPU H.264 encoding, keyframes every 0.5s)
  → Audio extract + normalization (dynaudnorm)
  → Whisper GPU / ElevenLabs API (transcription)
  → TransNetV2 (scene detection, PyTorch GPU)
  → Qwen2-VL-7B batch (embeddings, 3 frames/scene)
  → Elasticsearch (full-text indexing)

```

### Key Technologies

* **FFmpeg** - Transcoding, keyframes, audio normalization
* **NVENC** - GPU encoding H.264 (5-10x faster than CPU)
* **Whisper** - Audio transcription (OpenAI, CTranslate2 GPU)
* **TransNetV2** - Scene detection (PyTorch GPU)
* **Qwen2-VL-7B** - Multimodal embeddings (Flash Attention, batch inference)
* **Decord** - Video decoding GPU (5-10x faster than OpenCV)
* **Ollama** - Local LLM for metadata scraping
* **Rich** - Logging and progress bars

### Optimizations

* ✅ Batch processing for embeddings (batch_size=24)
* ✅ GPU parallel: transcribe + scene detection concurrently
* ✅ Decord instead of OpenCV for frame extraction
* ✅ Persistent volume for ML models (no re-downloading)
* ✅ Docker layer caching for fast rebuilds
* ✅ NVENC via NVIDIA runtime (no driver mounting)
* ✅ Central logging (all logs to stderr → docker logs)

### ML Models Cache (Persistent Volume)

Models downloaded automatically on first run:

* **Qwen2-VL-7B** (~15GB) - Multimodal embeddings
* **Whisper large-v3-turbo** (~3GB) - Audio transcription
* **TransNetV2** (~1GB) - Scene detection
* **Ollama qwen3-coder:30b** (~20GB) - LLM for scraping (optional)
* **PyTorch, CUDA libs** (~10GB)

**Total: ~50GB** (volume `ranchbot-ai-models`)

---

## 🔍 Troubleshooting

### Problem: NVENC not working (uses CPU libx264)

```bash
# Check if NVIDIA runtime is working
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi

# Check if FFmpeg sees NVENC
docker-compose run --rm preprocessor ffmpeg -encoders | grep nvenc

# If not seen, check logs
docker logs ranchbot-preprocessing-app | grep ENTRYPOINT

```

**Solution:**

* Ensure NVIDIA Container Toolkit is installed
* Check if `runtime: nvidia` is present in docker-compose.yml
* Restart Docker daemon

### Problem: No disk space

```bash
# Check volume size
docker volume inspect ranchbot-ai-models

# Clean unused images and volumes
docker system prune -a
docker volume prune

# Remove model cache (warning: re-download on next run)
docker volume rm ranchbot-ai-models

```

### Problem: Out of memory (CUDA OOM)

```bash
# Decrease batch_size for embeddings
../run-preprocessor.sh generate-embeddings --batch-size 12  # default 24

# Or use a smaller Whisper model
../run-preprocessor.sh transcribe --model medium  # instead of large-v3-turbo

```

### Problem: Container crashes

```bash
# Check logs (last 200 lines)
docker logs ranchbot-preprocessing-app --tail 200

# Check exit code
docker inspect ranchbot-preprocessing-app | grep ExitCode

# Run interactive bash
docker-compose run --rm preprocessor bash

```

### Problem: Slow processing

* Check `nvidia-smi` to see if GPU is being used (inside container)
* Increase `max_workers` for audio normalization (default 1)
* Use `--parallel-steps` in `run-all` (transcription + scenes concurrently)
* For embeddings: use `scene_changes` strategy + larger batch_size

### Problem: Logs are not visible

```bash
# Check if container is running
docker ps | grep preprocessor

# Check logs from different sources
docker-compose logs preprocessor
docker logs ranchbot-preprocessing-app

# Increase verbosity (--debug in future)

```

---

## 📈 Performance (RTX 3090, 64GB RAM)

**Full Pipeline (`run-all`):**

* 45-minute episode: **~20 minutes**
* 10 episodes (series): **~3.5 hours**

**Time Breakdown:**

* Transcode (NVENC): ~2 min
* Transcribe (Whisper GPU): ~5 min
* Scene detection (TransNetV2): ~3 min
* Embeddings (Qwen2-VL batch): ~8 min
* Index (Elasticsearch): ~2 min

**With Optimizations (`--parallel-steps`):**

* Parallel: Transcribe + Scene detection: **~5 min** (instead of 8)
* **Total time: ~17 min** (15% saving)

---

## 🚀 Performance Tips

### For High-End Systems (RTX 3090+, 64GB RAM)

**Option 1: Full pipeline with all optimizations**

```bash
../run-preprocessor.sh run-all /input_data/videos \
  --episodes-info-json /input_data/episodes.json \
  --name ranczo \
  --device cuda \
  --parallel-steps \
  --max-workers 2

```

**What it does:**

* ✅ Transcribe + Scene Detection **concurrently**
* ✅ Batch embeddings with Decord (5-10x faster)
* ✅ Multi-worker for audio normalization

**Option 2: Ramdisk for temp files** (requires 16GB+ free RAM)

```bash
# Setup ramdisk (Linux, one-time)
sudo mkdir -p /mnt/ramdisk
sudo mount -t tmpfs -o size=16G tmpfs /mnt/ramdisk

# Uncomment in docker-compose.yml:
# - /mnt/ramdisk:/mnt/ramdisk

# Run with ramdisk
../run-preprocessor.sh run-all /input_data/videos \
  --episodes-info-json /input_data/episodes.json \
  --name ranczo \
  --ramdisk-path /mnt/ramdisk \
  --parallel-steps

```

**Gain:** 20-30% faster audio normalization

---

## 📞 Need Help?

**Display all available commands:**

```bash
../run-preprocessor.sh --help

```

**Help for specific command:**

```bash
../run-preprocessor.sh transcode --help
../run-preprocessor.sh transcribe --help
../run-preprocessor.sh generate-embeddings --help

```

**Check main documentation:**

* [../README.md](https://www.google.com/search?q=../README.md) - Documentation for the entire RanczoKlipy Bot project

---

## ✅ Deployment Summary

**Sole method: Docker-only**

* ✅ Zero manual configuration
* ✅ Automatic GPU support
* ✅ All ML models in cache
* ✅ Logs visible in `docker logs`
* ✅ Simple wrapper `./run-preprocessor.sh`

```bash
# One-liner to run
../run-preprocessor.sh run-all /input_data/videos \
  --episodes-info-json /input_data/episodes.json \
  --name ranczo

```

**There is no manual installation option.** The preprocessor is designed and tested exclusively for execution in Docker.
# Video Preprocessing Pipeline - User Guide

A complete toolkit for processing video files: transcoding, transcription (Whisper/ElevenLabs), scene detection, embeddings generation, and indexing in Elasticsearch.

**🐳 Primary deployment method: Docker** (all dependencies, GPU support, models pre-cached)

---

## 📋 Table of Contents

- [Quick Start (Docker)](#-quick-start-docker-recommended)
- [Docker Guide (Full Details)](#-docker-guide)
- [Manual Installation](#manual-installation-alternative)
- [Requirements](#requirements)
- [Basic Workflows](#basic-workflows)
- [Command Reference](#command-reference)
- [Configuration Files](#configuration-files)
- [Performance Optimization](#-performance-tips)
- [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start (Docker - Recommended)

Docker provides the **fastest** and **most reliable** way to run the pipeline with all dependencies pre-configured.

### Prerequisites
- Docker with NVIDIA Container Toolkit
- NVIDIA GPU (RTX 3090 recommended)
- 64GB RAM (recommended for optimal performance)

### Setup (One-time)

```bash
cd /mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor

# Build image (includes CUDA, PyTorch, Whisper, all models)
docker-compose build

# Start container
docker-compose up -d

# Enter container
docker-compose exec preprocessor bash
```

### Run Complete Pipeline (Optimized for RTX 3090)

**Inside the container:**

```bash
# Full pipeline with ALL optimizations enabled:
python -m preprocessor run-all /videos \
    --episodes-info-json episodes.json \
    --name ranczo \
    --device cuda \
    --parallel-steps

# What this does:
# 1. Transcode videos (NVENC GPU)
# 2. [Transcribe (Whisper) || Scene Detection (TransNetV2)] ← parallel!
# 3. Generate embeddings (batch + decord + 3 frames/scene)
# 4. Index to Elasticsearch

# Performance: ~20min per 45-min episode (55% faster than sequential)
```

### Quick Commands Reference

```bash
# View help
python -m preprocessor --help

# Run individual steps
python -m preprocessor transcode /videos --episodes-info-json episodes.json
python -m preprocessor transcribe /videos --episodes-info-json episodes.json --name ranczo
python -m preprocessor detect-scenes /videos
python -m preprocessor generate-embeddings --transcription-jsons ./transcriptions --videos /videos

# Exit container
exit

# Stop container
docker-compose down
```

---

## 🐳 Docker Guide

### Why Docker?

✅ **Pre-configured environment** - CUDA 12.1, cuDNN, PyTorch, all Python packages
✅ **Model caching** - HuggingFace models, Whisper, TransNetV2 cached in volumes
✅ **GPU support** - NVIDIA Container Runtime pre-configured
✅ **Reproducible** - Same environment on any machine
✅ **No conflicts** - Isolated from host system

### Docker Compose Configuration

**File location:** `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/docker-compose.yml`

**Key features:**
- NVIDIA GPU runtime
- Persistent model cache volumes
- Volume mounts for input/output
- Ollama integration (for scraping)

### Volume Mounts

```yaml
volumes:
  - ./videos:/videos:ro                    # Input videos (read-only)
  - ./episodes.json:/app/episodes.json:ro  # Episode metadata
  - ./preprocessed:/app/preprocessed       # All outputs
  - model_cache:/app/.cache                # ML models (persistent)
  - ollama_models:/root/.ollama            # Ollama models (persistent)
```

**Output structure:**
```
preprocessed/
├── transcoded_videos/    # Step 1 output
├── transcriptions/       # Step 2 output
├── scene_timestamps/     # Step 3 output
└── embeddings/          # Step 4 output (optional)
```

### Managing Models

Models are automatically downloaded on first run and cached in Docker volumes.

**Check cached models:**
```bash
# Inside container
ls -lh /app/.cache/huggingface/  # HuggingFace models
ls -lh /app/.cache/whisper/      # Whisper models
ollama list                       # Ollama models
```

**Clear model cache (if needed):**
```bash
docker-compose down
docker volume rm ranczo-model-cache ranczo-ollama-models
docker-compose up -d  # Will re-download models
```

### GPU Configuration

**Use specific GPU:**
```bash
CUDA_VISIBLE_DEVICES=0 docker-compose up -d
```

**Use multiple GPUs** (edit `docker-compose.yml`):
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all  # Use all GPUs
          capabilities: [gpu]
```

### Docker Troubleshooting

**GPU not detected:**
```bash
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

**Rebuild after changes:**
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

**View logs:**
```bash
docker-compose logs -f preprocessor
```

**Free up space:**
```bash
docker system prune -a --volumes
```

---

## Manual Installation (Alternative)

**⚠️ Not recommended** - Manual installation requires managing CUDA, Python dependencies, and models yourself.

### Prerequisites

- Python 3.11+
- CUDA 12.1 + cuDNN
- FFmpeg with NVENC support
- 64GB RAM (for optimal performance)

### Install Steps

```bash
cd /mnt/c/GIT_REPO/RANCZO_KLIPY

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r preprocessor/requirements.txt
```

### Run Everything at Once

```bash
python -m preprocessor run-all /path/to/videos \
    --episodes-info-json episodes.json \
    --name my_series \
    --device cuda \
    --max-workers 2
```

This single command will:
1. Convert videos to standard format
2. Generate transcriptions
3. Index everything in Elasticsearch

**Use `--max-workers` to process multiple episodes in parallel!**

### Or Run Step-by-Step

```bash
# Step 1: Convert videos (2 episodes at once)
python -m preprocessor transcode /path/to/videos \
    --episodes-info-json episodes.json \
    --max-workers 2

# Step 2: Generate transcriptions (parallel audio normalization)
python -m preprocessor transcribe /path/to/videos \
    --episodes-info-json episodes.json \
    --name my_series \
    --max-workers 2

# Step 3: Index in Elasticsearch
python -m preprocessor index --name my_series --transcription-jsons ./transcriptions
```

---

## 💻 Requirements

### Option 1: Docker (Recommended)

- **Docker**: With NVIDIA Container Toolkit
- **NVIDIA GPU**: With CUDA support
- All models and dependencies included in the image

### Option 2: Manual Installation

- **Python**: 3.8 or newer
- **FFmpeg**: For video processing ([download here](https://ffmpeg.org/download.html))
- **Elasticsearch**: Running on localhost:9200
- **CUDA**: Optional, for GPU acceleration (10-50x faster)

---

## 📖 Basic Workflows

### Workflow 1: New Videos → Full Processing

**When to use**: You have video files and want to process them from scratch.

```bash
python -m preprocessor run-all /path/to/videos \
    --episodes-info-json episodes.json \
    --name my_series \
    --device cuda
```

### Workflow 2: Import Existing Transcriptions

**When to use**: You already have transcriptions from ElevenLabs and want to skip transcription.

```bash
python -m preprocessor import-transcriptions \
    --source-dir /path/to/11labs/output \
    --name my_series \
    --episodes-info-json episodes.json
```

Benefits: Much faster, no API costs, reuses existing work.

### Workflow 3: Generate New Transcriptions with ElevenLabs

**When to use**: You want high-quality transcriptions with speaker identification.

```bash
export ELEVEN_API_KEY=your_api_key_here

python -m preprocessor transcribe-elevenlabs /path/to/videos \
    --name my_series \
    --episodes-info-json episodes.json
```

Benefits: High accuracy, speaker diarization, multiple languages.

---

## 🔧 Command Reference

### 1. `transcode` - Convert Videos

**Purpose**: Standardize video format for consistent playback.

```bash
python -m preprocessor transcode /path/to/videos \
    --transcoded-videos ./output/videos \
    --resolution 1080p \
    --episodes-info-json episodes.json \
    --max-workers 2
```

**Common Options**:
- `--resolution`: Video quality (360p, 720p, 1080p, 2160p)
- `--codec`: Encoder (h264_nvenc for GPU, libx264 for CPU)
- `--crf`: Quality level (lower = better, default: 31)
- `--max-workers`: Process multiple episodes in parallel (default: 1)

### 2. `transcribe` - Generate Transcriptions (Whisper)

**Purpose**: Convert speech to text using local Whisper model.

```bash
python -m preprocessor transcribe /path/to/videos \
    --episodes-info-json episodes.json \
    --name my_series \
    --device cuda \
    --max-workers 2
```

**Common Options**:
- `--model`: Whisper model size
  - Fast: `tiny`, `base`
  - Balanced: `small`, `medium`
  - Accurate: `large-v3-turbo`
- `--language`: Transcription language (default: Polish)
- `--device`: Use `cuda` for GPU or `cpu` for CPU
- `--max-workers`: Parallel workers for audio normalization (default: 1)

### 3. `import-transcriptions` - Import Existing Files

**Purpose**: Use pre-generated transcriptions instead of creating new ones.

```bash
python -m preprocessor import-transcriptions \
    --source-dir /path/to/transcriptions \
    --name my_series \
    --episodes-info-json episodes.json
```

**Supported Formats**:
- `11labs_segmented`: ElevenLabs segmented JSON
- `11labs`: ElevenLabs full JSON

### 4. `transcribe-elevenlabs` - Generate with ElevenLabs API

**Purpose**: Create high-quality transcriptions with speaker identification.

```bash
python -m preprocessor transcribe-elevenlabs /path/to/videos \
    --name my_series \
    --api-key YOUR_API_KEY
```

**Common Options**:
- `--diarize`: Enable speaker identification (default: on)
- `--language-code`: Language (pol, eng, etc.)

### 5. `index` - Add to Elasticsearch

**Purpose**: Make transcriptions searchable.

```bash
python -m preprocessor index \
    --name my_series \
    --transcription-jsons ./transcriptions
```

**Common Options**:
- `--append`: Add to existing index (don't recreate)
- `--dry-run`: Test without actually indexing

### 6. `scrape-episodes` - Extract Episode Info from Web

**Purpose**: Automatically gather episode metadata from websites.

```bash
python -m preprocessor scrape-episodes \
    --urls https://filmweb.pl/serial/... \
    --output-file episodes.json \
    --llm-provider lmstudio
```

**Common Options**:
- `--urls`: Website URL (can use multiple times)
- `--llm-provider`: AI model to use (lmstudio, ollama, gemini)
- `--merge-sources`: Combine info from multiple sites

### 7. `detect-scenes` - Find Scene Changes

**Purpose**: Identify where scenes change in videos.

```bash
python -m preprocessor detect-scenes /path/to/videos \
    --output-dir ./scene_timestamps \
    --device cuda
```

**Common Options**:
- `--threshold`: Sensitivity (0.3 = sensitive, 0.7 = less sensitive)
- `--min-scene-len`: Minimum scene duration in frames

### 8. `generate-embeddings` - Create Semantic Search Data

**Purpose**: Enable AI-powered search by meaning, not just keywords. Uses GPU-accelerated batch inference with Decord video decoder for 5-10x speedup.

```bash
python -m preprocessor generate-embeddings \
    --transcription-jsons ./transcriptions \
    --videos ./transcoded_videos \
    --scene-timestamps-dir ./scene_timestamps \
    --batch-size 24 \
    --device cuda
```

**Common Options**:
- `--no-text`: Skip text embeddings
- `--no-video`: Skip video embeddings
- `--keyframe-strategy`: How to sample video
  - `scene_changes` (recommended): Uses scene timestamps, extracts 3 frames per scene (start, mid, end)
  - `keyframes`: Extract every 5 seconds
  - `color_diff`: Detect color/histogram changes
- `--keyframe-interval`: Process every Nth keyframe/scene (higher = faster but less detailed)
- `--batch-size`: Number of frames processed together (default: 24)
- `--max-workers`: Parallel workers for processing episodes (default: 1)
- `--scene-timestamps-dir`: Directory with scene detection JSON files (required for scene_changes strategy)

**Performance Tips for RTX 3090 (24GB VRAM)**:
- Model uses ~16GB VRAM, leaving ~8GB for batch processing
- Optimal batch size: 24-32 frames
- Use `--max-workers 1` for single GPU (model is too large for multi-worker on one GPU)
- Scene changes strategy with Decord provides 5-10x speedup vs OpenCV frame-by-frame
- For best results: Run `detect-scenes` first, then use `scene_changes` strategy

---

## 📁 Configuration Files

### Episode Metadata (`episodes.json`)

This file tells the system about your episodes:

```json
{
  "seasons": [
    {
      "season_number": 1,
      "episodes": [
        {
          "episode_number": 1,
          "title": "Pilot Episode",
          "premiere_date": "2006-03-05",
          "viewership": 4500000
        },
        {
          "episode_number": 2,
          "title": "Second Episode",
          "premiere_date": "2006-03-12",
          "viewership": 4600000
        }
      ]
    }
  ]
}
```

**Special Features (Season 0)**:
Season 0 is for bonus content (movies, deleted scenes, interviews):

```json
{
  "seasons": [
    {
      "season_number": 0,
      "episodes": [
        {
          "episode_number": 1,
          "title": "Behind the Scenes",
          "premiere_date": "2006-12-25",
          "viewership": 0
        }
      ]
    }
  ]
}
```

### Video File Naming

Videos must include episode numbers:
- ✅ `SeriesName_E01.mp4` → Season 1, Episode 1
- ✅ `Show_S02E05.mp4` → Season 2, Episode 5
- ❌ `video.mp4` → Won't be recognized

---

## 📂 Output Structure

After processing, your files will be organized like this:

```
transcoded_videos/
├── Sezon 1/
│   ├── series_S01E01.mp4
│   ├── series_S01E02.mp4
│   └── ...
├── Sezon 2/
│   └── ...
└── Specjalne/          # Season 0 (bonus content)
    └── ...

transcriptions/
├── Sezon 1/
│   ├── series_S01E01.json
│   └── ...
└── Sezon 2/
    └── ...

scene_timestamps/       # Optional: scene detection data
embeddings/            # Optional: semantic search data
```

---

## 🎯 Advanced Features

### GPU Acceleration

**10-50x faster transcription** with NVIDIA GPU:

```bash
python -m preprocessor transcribe /path/to/videos \
    --device cuda \
    --model large-v3-turbo
```

Without GPU (slower but works on any computer):

```bash
python -m preprocessor transcribe /path/to/videos \
    --device cpu \
    --model base
```

### Custom Video Quality

Balance quality vs file size:

```bash
python -m preprocessor transcode /path/to/videos \
    --crf 23        # Lower = better quality (18-28 recommended)
    --preset slow   # Slower encoding = better compression
```

### Multiple Language Support

Transcribe in different languages:

```bash
python -m preprocessor transcribe /path/to/videos \
    --language English
```

### Testing Before Full Run

Preview changes without committing:

```bash
python -m preprocessor index \
    --name my_series \
    --transcription-jsons ./transcriptions \
    --dry-run
```

---

## 🔍 Troubleshooting

### Problem: FFmpeg Not Found

**Solution**: Install FFmpeg:
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
- **Mac**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

### Problem: CUDA Out of Memory

**Solutions**:
1. Use smaller model: `--model small`
2. Switch to CPU: `--device cpu`
3. Process one video at a time

### Problem: Elasticsearch Connection Failed

**Check if running**:
```bash
curl http://localhost:9200
```

**Start Elasticsearch** if needed (varies by installation method).

### Problem: Episode Numbers Not Detected

**Fix**: Rename files to include episode numbers:
- From: `video1.mp4`
- To: `Show_E01.mp4`

### Problem: Transcription Too Slow

**Solutions**:
1. Use GPU: `--device cuda`
2. Use smaller model: `--model base`
3. Import existing transcriptions instead

---

## 💡 Performance Tips

### For High-End Systems (RTX 3090 + 64GB RAM)

**🚀 Recommended: Use optimized `run-all` command**

```bash
# Setup ramdisk (one-time, Linux):
sudo mkdir -p /mnt/ramdisk
sudo mount -t tmpfs -o size=16G tmpfs /mnt/ramdisk

# Run full pipeline with all optimizations:
python -m preprocessor run-all /videos \
    --episodes-info-json episodes.json \
    --name ranczo \
    --device cuda \
    --ramdisk-path /mnt/ramdisk \
    --parallel-steps
```

**What this does:**
- ✅ Transcribe + Scene Detection run **in parallel** (saves 30-40% time)
- ✅ Uses **ramdisk** for temporary files (20-30% faster audio normalization)
- ✅ **Batch embeddings** with Decord (5-10x faster than before)
- ✅ Complete pipeline: transcode → [transcribe || scenes] → embeddings → index

**Performance gain: ~55% faster** (44min → 20min per 45-min episode)

---

### General Tips

1. **Use GPU**: 10-50x faster for transcription
2. **Choose Right Model**:
   - Fast development: `base` or `small`
   - Production quality: `large-v3-turbo`
3. **Parallel Processing**: Use `--max-workers N` to process multiple episodes simultaneously
   ```bash
   # Process 4 episodes at once
   python -m preprocessor transcode /videos --episodes-info-json episodes.json --max-workers 4
   python -m preprocessor transcribe /videos --episodes-info-json episodes.json --name ranczo --max-workers 2
   ```
4. **Embedding Generation Optimization** (RTX 3090 or similar):
   - Use `scene_changes` strategy with batch processing for 5-10x speedup
   - Optimal batch size: 24-32 frames (adjust based on VRAM availability)
   - Run scene detection first for best results
   ```bash
   python -m preprocessor detect-scenes /videos --device cuda
   python -m preprocessor generate-embeddings \
       --transcription-jsons ./transcriptions \
       --videos /videos \
       --scene-timestamps-dir ./scene_timestamps \
       --batch-size 24 \
       --device cuda
   ```
5. **Ramdisk for Temp Files** (with 64GB+ RAM):
   - Mount tmpfs ramdisk for temporary audio files
   - Eliminates I/O bottleneck during audio normalization
   - Requires ~16GB free RAM
6. **Disk Space**: Ensure 2x video size available (transcoding creates copies)

### Parallelization Guidelines

**Transcoding** (`--max-workers`):
- CPU encoding: Workers = CPU cores / 2
- GPU encoding (NVENC): Workers = 2-4 (GPU has limited encoders)
- Example: 8-core CPU with GPU → `--max-workers 2`

**Transcription** (`--max-workers`):
- For audio normalization only (Whisper runs sequentially)
- CPU: Workers = CPU cores
- GPU: Workers = 2-4 (doesn't affect Whisper GPU usage)
- Example: 16-core CPU → `--max-workers 8`

**Full Pipeline** (`run-all --max-workers`):
- Conservative: `--max-workers 1` (default, sequential)
- Moderate: `--max-workers 2` (2 episodes in pipeline)
- Aggressive: `--max-workers 4` (requires good CPU/GPU)

---

## 📞 Getting Help

View all available commands:
```bash
python -m preprocessor --help
```

View help for specific command:
```bash
python -m preprocessor transcode --help
```

---

**Ready to start?** Jump to [Quick Start (Docker)](#-quick-start-docker-recommended) and process your first video in minutes!

---

## 🎯 Deployment Summary

**Primary (Recommended): Docker**
- ✅ Zero configuration
- ✅ GPU support built-in
- ✅ All models pre-cached
- ✅ Reproducible across systems
- 📍 Location: `/mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor/Dockerfile`

```bash
cd /mnt/c/GIT_REPO/RANCZO_KLIPY/preprocessor
docker-compose up -d
docker-compose exec preprocessor bash
python -m preprocessor run-all /videos --episodes-info-json episodes.json --name ranczo --device cuda --parallel-steps
```

**Alternative: Manual Installation**
- ⚠️ Requires manual CUDA/PyTorch setup
- ⚠️ Dependency management complexity
- Use only if Docker unavailable

---

## 🔬 Future Optimizations (TODO - To Test)

Additional performance improvements for consideration:

### 1. Multi-Episode Pipeline Staging
**Status:** Code ready (`pipeline_manager.py`), needs integration testing
- Different episodes in different pipeline stages simultaneously
- Example: Episode 1 (embeddings) | Episode 2 (transcribe) | Episode 3 (transcode)
- **Expected gain:** 30-40% better GPU utilization (GPU never idle)
- **Implementation:** Use `PipelineManager` class for advanced scheduling

### 2. Audio Normalization on GPU
**Status:** Requires FFmpeg CUDA filter testing
- Use FFmpeg CUDA filters instead of CPU dynaudnorm
- **Expected gain:** 2-3x faster audio normalization
- **Command to test:**
  ```bash
  ffmpeg -hwaccel cuda -hwaccel_output_format cuda \
         -i input.mp4 -af "loudnorm" output.wav
  ```

### 3. Whisper Batch Inference
**Status:** Needs verification if faster-whisper supports batch mode
- Process multiple audio files in one batch
- **Expected gain:** 20-30% faster transcription
- **To investigate:** Check if `faster-whisper` library supports batch transcription
  ```python
  # Current: Sequential
  for audio in files:
      result = model.transcribe(audio)

  # Target: Batch
  results = model.transcribe_batch(files)
  ```

**Note:** These optimizations are experimental and require testing before deployment.
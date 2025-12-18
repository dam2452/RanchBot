# Video Preprocessing Pipeline - User Guide

A complete toolkit for processing video files: transcoding, transcription (Whisper/ElevenLabs), and indexing in Elasticsearch.

---

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Requirements](#requirements)
- [Basic Workflows](#basic-workflows)
- [Command Reference](#command-reference)
- [Configuration Files](#configuration-files)
- [Advanced Features](#advanced-features)
- [Docker Guide](#docker-guide)
- [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start

### Option 1: Using Docker (Recommended)

**Build and run:**
```bash
cd preprocessor
docker-compose up -d
docker-compose exec preprocessor bash
```

**Inside container:**
```bash
init-models.sh
python -m preprocessor run-all /videos --episodes-info-json episodes.json --name ranczo --device cuda
```

### Option 2: Manual Installation

```bash
pip install -r requirements.txt
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

**Purpose**: Enable AI-powered search by meaning, not just keywords.

```bash
python -m preprocessor generate-embeddings \
    --transcription-jsons ./transcriptions \
    --videos ./transcoded_videos \
    --device cuda
```

**Common Options**:
- `--no-text`: Skip text embeddings
- `--no-video`: Skip video embeddings
- `--keyframe-strategy`: How to sample video (scene_changes recommended)
- `--keyframe-interval`: Process every Nth keyframe/scene (higher = faster but less detailed)

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
4. **Disk Space**: Ensure 2x video size available (transcoding creates copies)

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

## 🐳 Docker Guide

### Setup

**Prerequisites:**
- Docker with NVIDIA Container Toolkit installed
- NVIDIA GPU with CUDA support

**Installation:**
```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### Build Image

```bash
cd preprocessor
docker-compose build
```

This will:
- Install CUDA 12.1 with cuDNN
- Install Python 3.11, FFmpeg, Ollama
- Download Whisper models (large-v3-turbo)
- Download embedding model (gme-Qwen2-VL-7B-Instruct)
- Download TransNetV2 for scene detection
- Pull Ollama qwen3-coder:30b and configure with 50k context window

### Run Container

```bash
docker-compose up -d
docker-compose exec preprocessor bash
```

### Verify Models

```bash
init-models.sh
```

### Example Usage

```bash
python -m preprocessor run-all /videos \
    --episodes-info-json episodes.json \
    --name ranczo \
    --device cuda

python -m preprocessor generate-embeddings \
    --transcription-jsons ./transcriptions \
    --videos /videos \
    --device cuda

python -m preprocessor scrape-episodes \
    --urls https://example.com \
    --output-file episodes.json \
    --llm-provider ollama
```

### Volume Mounts

Docker compose automatically mounts:
- `./videos` → `/videos` (input videos)
- `./transcoded_videos` → `/app/transcoded_videos`
- `./transcriptions` → `/app/transcriptions`
- `./embeddings` → `/app/embeddings`
- `./scene_timestamps` → `/app/scene_timestamps`
- `./episodes.json` → `/app/episodes.json`
- Model cache (persistent volume)

### GPU Settings

To use specific GPU:
```bash
CUDA_VISIBLE_DEVICES=0 docker-compose up -d
```

To use multiple GPUs, edit `docker-compose.yml`:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all  # Use all GPUs
          capabilities: [gpu]
```

### Troubleshooting Docker

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

**Check logs:**
```bash
docker-compose logs -f preprocessor
```

**Free up space:**
```bash
docker system prune -a --volumes
```

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

**Ready to start?** Jump to [Quick Start](#quick-start) and process your first video in minutes!
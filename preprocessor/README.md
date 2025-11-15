# Video Preprocessing Pipeline

A comprehensive video preprocessing pipeline for transcoding, transcription generation, and Elasticsearch indexing of video content.

## Overview

This preprocessing pipeline provides a complete solution for processing video files through three main stages:

1. **Transcoding**: Convert videos to a standardized format and resolution using FFmpeg
2. **Transcription**: Generate audio transcriptions using OpenAI's Whisper model
3. **Indexing**: Index transcriptions in Elasticsearch for searchable content

## Quick Start

Przetwórz wideo i uzyskaj transkrypcję + indeksację w Elasticu jedną komendą:

```bash
# Install dependencies
pip install -r requirements.txt

# Uruchom pełny pipeline (transcode + transkrypcja + indeksacja)
python -m preprocessor all /path/to/video.mp4 \
    --episodes-info-json episodes.json \
    --name my_series

# Wynik:
# - transcoded_videos/ - przetworzone wideo
# - transcriptions/ - JSON z transkrypcją
# - Elasticsearch index "my_series" - wyindeksowana transkrypcja
```

Wymagania: Python 3.8+, FFmpeg, Elasticsearch (localhost:9200)

## Features

- 🎬 **Video Transcoding**: Standardize videos with configurable resolution, codec, and quality settings
- 🎙️ **Audio Transcription**: High-quality speech-to-text using Whisper models
- 🔍 **Elasticsearch Integration**: Full-text search capabilities for video content
- 📊 **Episode Metadata**: Automatic organization with season/episode information
- 🎨 **Rich Console Output**: Beautiful terminal UI with progress indicators
- ⚡ **Efficient Processing**: Temporary file management and pipeline optimization

## Requirements

### System Dependencies

- **Python**: 3.8 or higher
- **FFmpeg**: For video/audio processing
- **FFprobe**: For media file inspection (usually included with FFmpeg)
- **CUDA** (optional): For GPU-accelerated transcription

### Python Dependencies

Install required packages:

```bash
pip install click rich elasticsearch openai-whisper
```

For GPU support (recommended for transcription):

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

## Installation

1. Ensure FFmpeg is installed and available in your system PATH:

```bash
ffmpeg -version
```

2. Install Python dependencies:

```bash
cd /path/to/RANCZO_KLIPY
pip install -r requirements.txt
```

3. Verify Elasticsearch is running (for indexing):

```bash
curl -X GET "localhost:9200/"
```

## Usage

The preprocessor provides four main commands:

### 1. Transcode Videos

Convert videos to a standardized format:

```bash
python -m preprocessor transcode /path/to/videos \
    --transcoded-videos ./output/videos \
    --resolution 1080p \
    --codec h264_nvenc \
    --preset slow \
    --crf 31 \
    --episodes-info-json episodes.json
```

**Options:**

- `videos`: Path to input videos directory (required)
- `--transcoded-videos`: Output directory for transcoded videos (default: `transcoded_videos`)
- `--resolution`: Target resolution: 360p, 480p, 720p, 1080p, 1440p, 2160p (default: `1080p`)
- `--codec`: Video codec (default: `h264_nvenc`)
- `--preset`: FFmpeg encoding preset (default: `slow`)
- `--crf`: Constant Rate Factor - quality setting, lower is better (default: `31`)
- `--gop-size`: Keyframe interval in seconds (default: `0.5`)
- `--episodes-info-json`: JSON file with episode metadata

### 2. Generate Transcriptions

Create audio transcriptions from videos using Whisper:

```bash
python -m preprocessor transcribe /path/to/videos \
    --episodes-info-json episodes.json \
    --name ranczo \
    --transcription-jsons ./output/transcriptions \
    --model large-v3-turbo \
    --language Polish \
    --device cuda
```

**Options:**

- `videos`: Path to input videos directory (required)
- `--episodes-info-json`: JSON file with episode metadata (required)
- `--name`: Series name for output files (required)
- `--transcription-jsons`: Output directory for transcription JSONs (default: `transcriptions`)
- `--model`: Whisper model name (default: `large-v3-turbo`)
  - Available models: `tiny`, `base`, `small`, `medium`, `large`, `large-v2`, `large-v3-turbo`
- `--language`: Language for transcription (default: `Polish`)
- `--device`: Device to use: `cuda` or `cpu` (default: `cuda`)
- `--extra-json-keys`: Additional JSON keys to remove from output (can be specified multiple times)

### 3. Index in Elasticsearch

Index transcriptions for full-text search:

```bash
python -m preprocessor index \
    --name ranczo \
    --transcription-jsons ./output/transcriptions \
    --append
```

**Options:**

- `--name`: Name of the Elasticsearch index (required)
- `--transcription-jsons`: Directory containing transcription JSON files (required)
- `--dry-run`: Validate data without sending to Elasticsearch (flag)
- `--append`: Append to existing index instead of recreating (flag)

### 4. Complete Pipeline

Run all stages sequentially:

```bash
python -m preprocessor all /path/to/videos \
    --episodes-info-json episodes.json \
    --name ranczo \
    --transcoded-videos ./output/videos \
    --transcription-jsons ./output/transcriptions \
    --resolution 1080p \
    --model large-v3-turbo \
    --language Polish \
    --device cuda
```

This command combines all three stages: transcoding → transcription → indexing.

## Episode Metadata Format

The `episodes.json` file should follow this structure:

```json
{
  "seasons": [
    {
      "season_number": 1,
      "episodes": [
        {
          "episode_number": 1,
          "title": "Episode Title",
          "premiere_date": "2006-03-05",
          "viewership": 4500000
        },
        {
          "episode_number": 2,
          "title": "Another Episode",
          "premiere_date": "2006-03-12",
          "viewership": 4600000
        }
      ]
    }
  ]
}
```

## Output Structure

### Transcoded Videos

```
transcoded_videos/
├── Sezon 1/
│   ├── ranczo_S01E01.mp4
│   ├── ranczo_S01E02.mp4
│   └── ...
└── Sezon 2/
    ├── ranczo_S02E01.mp4
    └── ...
```

### Transcription JSONs

```
transcriptions/
├── Sezon 1/
│   ├── ranczo_S01E01.json
│   ├── ranczo_S01E02.json
│   └── ...
└── Sezon 2/
    ├── ranczo_S02E01.json
    └── ...
```

Each transcription JSON contains:

```json
{
  "episode_info": {
    "season": 1,
    "episode_number": 1,
    "title": "Episode Title",
    "premiere_date": "2006-03-05",
    "viewership": 4500000
  },
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 5.5,
      "text": "Transcribed text here...",
      "author": "",
      "comment": "",
      "tags": [],
      "location": "",
      "actors": []
    }
  ]
}
```

## Advanced Usage

### Custom Video Naming

Videos should be named with episode numbers for proper organization:

- `SeriesName_E01.mp4` → Season 1, Episode 1
- `SeriesName_E02.mp4` → Season 1, Episode 2

The preprocessor uses the episode metadata JSON to map absolute episode numbers to season/episode combinations.

### GPU Acceleration

For faster transcription, use CUDA-enabled GPU:

```bash
python -m preprocessor transcribe /path/to/videos \
    --device cuda \
    --model large-v3-turbo \
    ...
```

To use CPU only:

```bash
python -m preprocessor transcribe /path/to/videos \
    --device cpu \
    --model base \
    ...
```

### Dry Run Mode

Test Elasticsearch indexing without actually sending data:

```bash
python -m preprocessor index \
    --name ranczo \
    --transcription-jsons ./transcriptions \
    --dry-run
```

## Architecture

### Module Structure

```
preprocessor/
├── __main__.py                    # CLI entry point with Click commands
├── config.py                      # Configuration dataclasses
├── video_transcoder.py            # Video transcoding logic
├── transciption_generator.py      # Transcription orchestration
├── elastic_search_indexer.py     # Elasticsearch indexing
├── convert_legacy_episodes_info.py # Legacy format converter
├── utils/
│   ├── args.py                    # Argument parsing utilities
│   └── error_handling_logger.py  # Rich-enhanced logging
└── transcriptions/
    ├── audio_normalizer.py        # Audio extraction and normalization
    ├── normalized_audio_processor.py # Whisper transcription
    ├── json_generator.py          # JSON processing and cleanup
    └── episode_info_processor.py  # Episode metadata integration
```

### Pipeline Flow

```
Videos → Transcode → Extract Audio → Normalize Audio →
Transcribe with Whisper → Process JSONs → Add Episode Info →
Index in Elasticsearch
```

## Troubleshooting

### FFmpeg Not Found

Ensure FFmpeg is installed and in your PATH:

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

### CUDA Out of Memory

If GPU runs out of memory during transcription:

1. Use a smaller Whisper model: `--model base` or `--model small`
2. Switch to CPU: `--device cpu`
3. Process videos one at a time

### Elasticsearch Connection Error

Verify Elasticsearch is running:

```bash
curl -X GET "localhost:9200/_cluster/health?pretty"
```

Check connection settings in the bot configuration.

### Episode Number Not Detected

Ensure video files follow the naming pattern:

- Must contain `E` followed by episode number: `E01`, `E02`, etc.
- Example: `Ranczo_E01.mp4`, `Show_S01E01.mp4`

## Performance Tips

1. **GPU Acceleration**: Use CUDA for Whisper transcription (10-50x faster)
2. **Parallel Processing**: Process multiple videos by running separate preprocessor instances
3. **Model Selection**: Balance speed vs accuracy:
   - Fast: `tiny`, `base`
   - Balanced: `small`, `medium`
   - Accurate: `large`, `large-v3-turbo`
4. **Storage**: Ensure sufficient disk space (transcoding can double storage requirements)

## Legacy Format Conversion

If you have episode data in the old format:

```bash
python -m preprocessor.convert_legacy_episodes_info \
    old_episodes.json \
    new_episodes.json
```

This converts from the legacy format to the current structure.

## Examples

### Basic Workflow

```bash
# Step 1: Transcode videos
python -m preprocessor transcode ./raw_videos \
    --episodes-info-json episodes.json \
    --resolution 1080p

# Step 2: Generate transcriptions
python -m preprocessor transcribe ./raw_videos \
    --episodes-info-json episodes.json \
    --name ranczo \
    --device cuda

# Step 3: Index in Elasticsearch
python -m preprocessor index \
    --name ranczo \
    --transcription-jsons ./transcriptions
```

### Complete Pipeline (All in One)

```bash
python -m preprocessor all ./raw_videos \
    --episodes-info-json episodes.json \
    --name ranczo \
    --device cuda
```

## License

This preprocessor is part of the Ranczo Klipy project.

## Support

For issues and questions, please refer to the main project documentation or create an issue in the project repository.

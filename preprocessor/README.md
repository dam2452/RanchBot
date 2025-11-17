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
python -m preprocessor run-all /path/to/video.mp4 \
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

### 2a. Import Existing Transcriptions (11labs)

Import pre-generated transcriptions from 11labs or other sources:

```bash
python -m preprocessor import-transcriptions \
    --source-dir C:\GIT_REPO\testParakeet\11labs\output_ranczo\segmented_json \
    --output-dir ./transcriptions \
    --episodes-info-json episodes.json \
    --name ranczo \
    --format-type 11labs_segmented
```

**Options:**

- `--source-dir`: Directory containing source transcription files (required)
- `--output-dir`: Output directory for converted transcriptions (default: `transcriptions`)
- `--episodes-info-json`: JSON file with episode metadata (optional)
- `--name`: Series name (required)
- `--format-type`: Source format type (default: `11labs_segmented`)
  - `11labs_segmented`: 11labs segmented JSON format
  - `11labs`: 11labs full JSON format
- `--no-state`: Disable state management and progress tracking

**Example with existing Ranczo transcriptions:**

```bash
# Import all Ranczo transcriptions from 11labs
python -m preprocessor import-transcriptions \
    --source-dir "C:\GIT_REPO\testParakeet\11labs\output_ranczo\segmented_json" \
    --name ranczo \
    --episodes-info-json episodes.json

# Import Kapitan Bomba transcriptions
python -m preprocessor import-transcriptions \
    --source-dir "C:\GIT_REPO\testParakeet\11labs\kapitan_bomba-wideo" \
    --name kapitan_bomba \
    --format-type 11labs
```

**Benefits:**
- ⚡ Much faster than re-transcribing (reuse existing work)
- 💰 No API costs (use pre-generated transcriptions)
- ✅ Support for 11labs high-quality transcriptions
- 📊 Progress tracking and resume support

### 2b. Generate Transcriptions with 11labs API

Use 11labs API to generate new high-quality transcriptions with speaker diarization:

```bash
python -m preprocessor transcribe-elevenlabs /path/to/videos \
    --name ranczo \
    --episodes-info-json episodes.json \
    --api-key YOUR_ELEVEN_LABS_API_KEY \
    --language-code pol \
    --diarize
```

**Options:**

- `videos`: Path to input videos directory (required)
- `--name`: Series name (required)
- `--output-dir`: Output directory for transcriptions (default: `transcriptions`)
- `--episodes-info-json`: JSON file with episode metadata (optional)
- `--api-key`: ElevenLabs API key (or set `ELEVEN_API_KEY` env var)
- `--model-id`: ElevenLabs model ID (default: `scribe_v1`)
- `--language-code`: Language code (default: `pol`)
- `--diarize/--no-diarize`: Enable speaker diarization (default: enabled)
- `--no-state`: Disable state management

**Example with environment variable:**

```bash
# Set API key
export ELEVEN_API_KEY=your_api_key_here

# Transcribe videos
python -m preprocessor transcribe-elevenlabs /videos/ranczo \
    --name ranczo \
    --episodes-info-json episodes.json \
    --language-code pol
```

**Benefits:**
- 🎯 High accuracy with speaker diarization
- 🗣️ Identifies different speakers automatically
- 🌍 Supports multiple languages
- 📊 Progress tracking and resume support
- ⚡ GPU-accelerated processing on 11labs servers

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
python -m preprocessor run-all /path/to/videos \
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

### 5. Scrape Episode Descriptions

Scrape episode metadata from web pages using Playwright and LLM:

```bash
python -m preprocessor scrape-episodes \
    --urls https://example.com/episode1 \
    --urls https://example.com/episode2 \
    --output-file episode_metadata.json \
    --llm-provider lmstudio
```

**Options:**

- `--urls`: URL to scrape (can be specified multiple times for multiple sources)
- `--output-file`: Output JSON file path (required)
- `--llm-provider`: LLM provider to use: `lmstudio` (default), `ollama`, or `gemini`
- `--llm-api-key`: API key for LLM (required for Gemini, can use `GEMINI_API_KEY` env var)
- `--llm-model`: Override default model name
- `--headless/--no-headless`: Run browser in headless mode (default: headless)
- `--merge-sources/--no-merge`: Merge data from multiple sources (default: merge)

**Example with multiple sources:**

```bash
python -m preprocessor scrape-episodes \
    --urls https://filmweb.pl/serial/Ranczo-2006-276093/season/1/episode/1 \
    --urls https://wikipedia.org/wiki/Ranczo_S01E01 \
    --urls https://imdb.com/title/tt0123456 \
    --output-file ranczo_S01E01_metadata.json \
    --llm-provider lmstudio
```

**Example with Gemini:**

```bash
export GEMINI_API_KEY=your_api_key_here
python -m preprocessor scrape-episodes \
    --urls https://example.com/episode \
    --output-file metadata.json \
    --llm-provider gemini
```

**How it works:**
1. Opens each URL with Playwright (stealth mode)
2. Extracts all text content from the page
3. Sends text to LLM for structured extraction
4. Merges results from multiple sources (if enabled)
5. Saves to JSON with episode metadata

**Output format:**

```json
{
  "sources": ["url1", "url2"],
  "merged_metadata": {
    "title": "Episode Title",
    "description": "Short 1-2 sentence description",
    "summary": "Detailed 3-5 sentence summary",
    "season": 1,
    "episode_number": 1
  }
}
```

### 6. Convert Legacy Elasticsearch Index

Convert old Elasticsearch documents to new format (ad-hoc script):

```bash
python -m preprocessor convert-elastic \
    --index-name ranczo \
    --backup-file backup.json \
    --dry-run
```

**Options:**

- `--index-name`: Name of the Elasticsearch index to convert (required)
- `--backup-file`: Backup file path before conversion (optional)
- `--dry-run`: Show sample converted document without updating (flag)

**Example workflow:**

```bash
# Step 1: Dry run to preview changes
python -m preprocessor convert-elastic \
    --index-name ranczo \
    --dry-run

# Step 2: Create backup and convert
python -m preprocessor convert-elastic \
    --index-name ranczo \
    --backup-file ./backups/ranczo_backup.json
```

**What it does:**
- Fetches all documents from the index
- Adds missing fields: `transcription`, `scene_timestamps`, `text_embeddings`, `video_embeddings`
- Converts legacy `text/start/end` to `transcription.segments` format
- Updates documents in Elasticsearch with bulk operation

**Note:** This is an ad-hoc script for one-time migration. After conversion, use only the new structure.

### 7. Scene Detection

Detect scene cuts in videos using TransNetV2 or histogram-based method:

```bash
python -m preprocessor detect-scenes /path/to/videos \
    --output-dir ./scene_timestamps \
    --threshold 0.5 \
    --min-scene-len 10 \
    --device cuda
```

**Options:**

- `videos`: Path to video file or directory (required)
- `--output-dir`: Output directory for scene JSON files (default: `scene_timestamps`)
- `--threshold`: Scene detection threshold (default: `0.5`)
- `--min-scene-len`: Minimum scene length in frames (default: `10`)
- `--device`: Device to use: `cuda` or `cpu` (default: `cuda`)

**Example:**

```bash
# Detect scenes in all videos
python -m preprocessor detect-scenes ./transcoded_videos \
    --threshold 0.5 \
    --device cuda

# Single video with custom settings
python -m preprocessor detect-scenes video.mp4 \
    --output-dir ./scenes \
    --threshold 0.3 \
    --min-scene-len 15
```

**Output format:**

```json
{
  "total_scenes": 45,
  "video_info": {
    "fps": 25.0,
    "duration": 1234.56,
    "total_frames": 30864
  },
  "detection_settings": {
    "threshold": 0.5,
    "min_scene_len": 10,
    "method": "transnetv2"
  },
  "scenes": [
    {
      "scene_number": 1,
      "start": {
        "frame": 0,
        "seconds": 0.0,
        "timecode": "00:00:00:00"
      },
      "end": {
        "frame": 125,
        "seconds": 5.0,
        "timecode": "00:00:05:00"
      },
      "duration": 5.0,
      "frame_count": 125
    }
  ]
}
```

**Methods:**
- **TransNetV2** (if installed): Deep learning-based scene detection (recommended)
- **Histogram-based** (fallback): Color histogram difference detection

### 8. Generate Embeddings

Generate text and video embeddings for semantic search:

```bash
python -m preprocessor generate-embeddings \
    --transcription-jsons ./transcriptions \
    --videos ./transcoded_videos \
    --device cuda \
    --keyframe-strategy scene_changes
```

**Options:**

- `--transcription-jsons`: Directory with transcription JSON files (required)
- `--videos`: Videos directory for video embeddings (optional)
- `--output-dir`: Output directory (default: `embeddings`)
- `--model`: Model name (default: `Alibaba-NLP/gme-Qwen2-VL-7B-Instruct`)
- `--segments-per-embedding`: Segments to group for text embeddings (default: `5`)
- `--keyframe-strategy`: Strategy for video embeddings (default: `scene_changes`)
  - `keyframes`: Extract every N frames
  - `scene_changes`: Use scene timestamps (recommended)
  - `color_diff`: Detect color/histogram changes
- `--generate-text/--no-text`: Generate text embeddings (default: enabled)
- `--generate-video/--no-video`: Generate video embeddings (default: enabled)
- `--device`: Device to use: `cuda` or `cpu` (default: `cuda`)
- `--scene-timestamps-dir`: Scene timestamps directory (for scene_changes strategy)

**Example - Text only:**

```bash
python -m preprocessor generate-embeddings \
    --transcription-jsons ./transcriptions \
    --no-video \
    --segments-per-embedding 5
```

**Example - Video only:**

```bash
python -m preprocessor generate-embeddings \
    --transcription-jsons ./transcriptions \
    --videos ./transcoded_videos \
    --no-text \
    --keyframe-strategy scene_changes \
    --device cuda
```

**Example - Both with GPU:**

```bash
python -m preprocessor generate-embeddings \
    --transcription-jsons ./transcriptions \
    --videos ./transcoded_videos \
    --device cuda \
    --keyframe-strategy scene_changes \
    --segments-per-embedding 5
```

**How it works:**
1. **Text embeddings**: Groups N segments, combines text, generates embedding
2. **Video embeddings**: Extracts keyframes based on strategy, generates embedding per frame
3. **GPU acceleration**: Runs model on GPU for faster processing
4. **Updates JSONs**: Adds embeddings directly to transcription JSON files

**Output format (added to transcription JSONs):**

```json
{
  "text_embeddings": [
    {
      "segment_range": [0, 4],
      "text": "Combined text from 5 segments...",
      "embedding": [0.123, -0.456, 0.789, ...]
    }
  ],
  "video_embeddings": [
    {
      "frame_number": 125,
      "timestamp": 5.0,
      "type": "scene_mid",
      "embedding": [0.234, -0.567, 0.890, ...]
    }
  ]
}
```

**Note:** Embeddings are stored but not yet used by search. This is preparation for future semantic search features.

### 9. Season 0 - Special Features

Season 0 is reserved for special materials (movies, deleted scenes, making of, interviews, etc.):

**How it works:**

- Episodes with `season: 0` in episode_info are automatically marked as special features
- Files are organized in `Specjalne/` directory instead of `Sezon 0/`
- Elasticsearch documents include:
  - `is_special_feature: true`
  - `special_feature_type: "special"` (can be customized)

**Example episodes.json with Season 0:**

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
        },
        {
          "episode_number": 2,
          "title": "Deleted Scenes",
          "premiere_date": "2007-01-01",
          "viewership": 0
        }
      ]
    },
    {
      "season_number": 1,
      "episodes": [...]
    }
  ]
}
```

**Directory structure:**

```
transcoded_videos/
├── Specjalne/              # Season 0
│   ├── series_S00E01.mp4
│   ├── series_S00E02.mp4
│   └── ...
├── Sezon 1/
│   ├── series_S01E01.mp4
│   └── ...
└── Sezon 2/
    └── ...

transcriptions/
├── Specjalne/              # Season 0
│   ├── series_S00E01.json
│   └── ...
└── Sezon 1/
    └── ...
```

**Special feature types:**

You can customize `special_feature_type` in episode_info:
- `"special"` - General special features (default)
- `"movie"` - Full-length movies
- `"deleted"` - Deleted scenes
- `"making_of"` - Making of / behind the scenes
- `"interview"` - Interviews

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
├── elevenlabs_transcriber.py     # ElevenLabs API transcription
├── transcription_importer.py     # Import existing transcriptions
├── episode_scraper.py            # Web scraping for episode metadata
├── scene_detector.py             # Scene detection with TransNetV2
├── embedding_generator.py        # Text/video embedding generation
├── legacy_converter.py           # Elasticsearch migration tool
├── state_manager.py              # Progress tracking and resume
├── llm_provider.py               # LLM provider abstraction
├── convert_legacy_episodes_info.py # Legacy format converter
├── engines/
│   ├── base_engine.py            # Base engine interface
│   ├── whisper_engine.py         # Whisper transcription engine
│   ├── elevenlabs_engine.py      # ElevenLabs API engine
│   ├── scraper_clipboard.py      # Clipboard scraper
│   └── scraper_crawl4ai.py       # Crawl4AI web scraper
├── utils/
│   ├── args.py                    # Argument parsing utilities
│   ├── error_handling_logger.py  # Rich-enhanced logging
│   ├── episode_utils.py          # Episode number utilities
│   ├── video_utils.py            # Video processing utilities
│   └── transcription_utils.py    # Transcription format utilities
└── transcriptions/
    ├── base_generator.py          # Base transcription generator
    ├── audio_normalizer.py        # Audio extraction and normalization
    ├── normalized_audio_processor.py # Whisper transcription
    ├── json_generator.py          # JSON processing and cleanup
    ├── episode_info_processor.py  # Episode metadata integration
    ├── full_json_generator.py     # Full JSON format generator
    ├── segmented_json_generator.py # Segmented JSON format generator
    ├── simple_json_generator.py   # Simple JSON format generator
    ├── srt_generator.py           # SRT subtitle generator
    ├── txt_generator.py           # Plain text generator
    └── multi_format_generator.py  # Multi-format output generator
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
python -m preprocessor run-all ./raw_videos \
    --episodes-info-json episodes.json \
    --name ranczo \
    --device cuda
```

## License

This preprocessor is part of the Ranczo Klipy project.

## Support

For issues and questions, please refer to the main project documentation or create an issue in the project repository.

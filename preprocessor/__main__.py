import logging
from pathlib import Path
import sys

from bot.utils.resolution import Resolution
from preprocessor.elastic_search_indexer import ElasticSearchIndexer
from preprocessor.transciption_generator import TranscriptionGenerator
from preprocessor.utils.args import (
    ParserModes,
    parse_multi_mode_args,
)
from preprocessor.video_transcoder import VideoTranscoder

# enter handlers in a valid order
MODE_WORKERS = {
        "all": [
            VideoTranscoder,
            TranscriptionGenerator,
            ElasticSearchIndexer,
        ],

        "transcode": [
            VideoTranscoder,
        ],

        "transcribe": [
            TranscriptionGenerator,
        ],

        "index": [
            ElasticSearchIndexer,
        ],
}


def generate_parser_modes() -> ParserModes:
    parser_modes = {
        "transcribe": [
            (
                "videos", {
                     "type": Path,
                     "help": "Path to input videos for preprocessing",
                },
            ),
            (
                "--episodes-info-json", {
                    "type": Path,
                    "help": "JSON with info for all episodes",
                },
            ),
            (
                "--transcription_jsons", {
                    "type": Path,
                    "default": TranscriptionGenerator.DEFAULT_OUTPUT_DIR,
                    "help": "Path for output transcriptions JSONs",
                },
            ),
            (
                "--model", {
                    "type": str,
                    "default": TranscriptionGenerator.DEFAULT_MODEL,
                    "help": "Whisper model to use",
                },
            ),
            (
                "--language", {
                    "type": str,
                    "default": TranscriptionGenerator.DEFAULT_LANGUAGE,
                    "help": "Language to use",
                },
            ),
            (
                "--device", {
                    "type": str,
                    "default": TranscriptionGenerator.DEFAULT_DEVICE,
                    "help": "Device to use",
                },
            ),
            (
                "--extra_json_keys_to_remove", {
                    "type": str,
                    "nargs": "*",
                    "default": [],
                    "help": "Additional keys to remove from JSONs",
                },
            ),
        ],

        "transcode": [
            (
                "videos", {
                     "type": Path,
                     "help": "Path to input videos for preprocessing",
                },
            ),
            (
                "--transcoded_videos", {
                   "type": Path,
                   "default": VideoTranscoder.DEFAULT_OUTPUT_DIR,
                   "help": "Path for output videos after transcoding",
                },
            ),
            (
                "--resolution", {
                    "type": Resolution.from_str,
                    "choices": list(Resolution),
                    "default": Resolution.R1080P,
                    "help": "Target resolution for all videos",
                },

            ),

            (
                "--codec", {
                   "type": str,
                   "default": VideoTranscoder.DEFAULT_CODEC,
                   "help": "Video codec",
                },
            ),
            (
                "--preset", {
                   "type": str,
                   "default": VideoTranscoder.DEFAULT_PRESET,
                   "help": "FFmpeg preset",
                },
            ),
            (
                "--crf", {
                    "type": int,
                    "default": VideoTranscoder.DEFAULT_CRF,
                    "help": "Quality (lower = better)",
                },
            ),
            (
                "--gop-size", {
                    "type": float,
                    "default": VideoTranscoder.DEFAULT_GOP_SIZE,
                    "help": "Keyframe interval in seconds",
                },
            ),
        ],

        "index": [
            (
                "--dry-run", {
                    "action": "store_true",
                    "help": "Validate data without sending to Elasticsearch.",
                },
            ),
            (
                "--name", {
                    "type": str,
                    "help": "Name of the ElasticSearch index",
                },
            ),
        ],
    }

    unique_flag_names = set()
    unique_flags = []

    for flags in parser_modes.values():
        for name, flag in flags:
            if name not in unique_flag_names:
                unique_flag_names.add(name)
                unique_flags.append((name, flag))

    parser_modes["all"] = unique_flags

    # So the help messages are not overwritten for the "all" mode.
    # We want to display the transcribe/transcode messages for the whole pipeline.
    parser_modes["index"] += [
        (
            "--transcoded_videos", {
                "type": Path,
                "help": "Transcoded videos for the ElasticSearch indexing",
            },
        ),
        (
            "--transcription_jsons", {
                "type": Path,
                "help": "Transcriptions in JSON files for the ElasticSearch indexing",
            },
        ),
    ]

    return parser_modes


if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.DEBUG)

    args = parse_multi_mode_args(
        description="Generate JSON audio transcriptions or transcode videos to an acceptable resolution.",
        modes=generate_parser_modes(),
        mode_helps={
            "transcode": "Transcode videos to a format expected by thebot",
            "transcribe": "Generate audio transcriptions (episode info included)",
            "index": "Index videos and transcriptions in ElasticSearch",
            "all": "Transcode videos, generate audio transcriptions and then pass results to ElasticSearch indexing",
        },
    )

    return_codes = []

    for worker in MODE_WORKERS[args["mode"]]:
        return_codes.append(
            worker(args).work(),
        )

    sys.exit(max(return_codes))

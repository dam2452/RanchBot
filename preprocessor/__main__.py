import logging
from pathlib import Path

from transciption_generator import TranscriptionGenerator
from video_transcoder import VideoTranscoder

from bot.utils.resolution import Resolution
from preprocessor.utils.args import (
    ParserModes,
    parse_multi_mode_args,
)


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
                "--transcription_jsons_dir", {
                    "type": Path,
                    "default": "", # todo
                    "help": "Path for output transcriptions JSONs",
                },
            ),

            # todo

        ],

        "transcode": [
            (
                "videos", {
                     "type": Path,
                     "help": "Path to input videos for preprocessing",
                },
            ),

            (
                "--transcoded_videos_dir", {
                   "type": Path,
                   "default": VideoTranscoder.DEFAULT_OUTPUT_DIR,
                   "help": "Path for output videos after transcoding",
                },
            ),
            (
                "--resolution", {
                   "type": lambda x: Resolution[x.upper()],
                   "choices": list(Resolution),
                   "default": Resolution.R1080P,
                   "help": "Target resolution for all videos.",
                },
            ),
            (
                "--codec", {
                   "type": str,
                   "default": VideoTranscoder.DEFAULT_CODEC,
                   "help": "Video codec.",
                },
            ),
            (
                "--preset", {
                   "type": str,
                   "default": VideoTranscoder.DEFAULT_PRESET,
                   "help": "FFmpeg preset.",
                },
            ),
            (
                "--crf", {
                    "type": int,
                    "default": VideoTranscoder.DEFAULT_CRF,
                    "help": "Quality (lower = better).",
                },
            ),
            (
                "--gop-size", {
                    "type": float,
                    "default": VideoTranscoder.DEFAULT_GOP_SIZE,
                    "help": "Keyframe interval in seconds.",
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

    return parser_modes

if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.DEBUG)


    args = parse_multi_mode_args(
        description="Generate JSON audio transcriptions or transcode videos to an acceptable resolution.",
        modes = generate_parser_modes(),
    )


    mode_workers = {
        "all": [
            VideoTranscoder,
            TranscriptionGenerator,
        ],

        "transcode": [
            VideoTranscoder,
        ],

        "transcribe": [
            TranscriptionGenerator,
        ],
    }

    print(args)


    # add defaults from classes here

    exit(0)


    #TranscriptionGenerator(args.videos, args.transcription_jsons_dir).transcribe()
    #VideoTranscoder(args.videos, args.transcoded_videos_dir).transcode()

    # pass transcriptions to elastic
    # split two paths to be async


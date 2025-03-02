import argparse
import logging
from pathlib import Path

from transciption_generator import TranscriptionGenerator
from video_transcoder import VideoTranscoder


if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.DEBUG)

    parser = argparse.ArgumentParser()
    parser.add_argument("videos", type=Path, help="Path to input videos for preprocessing")

    # 2 subparsers to split stuff
    # add defaults from classes here
    parser.add_argument("--transcoded-videos-dir", "-v", type=Path, default="transcoded_videos", help="Path for output videos after transcoding")
    parser.add_argument("--transcription-jsons-dir", "-j", type=Path, default="transcriptions", help="Path for output transcriptions JSONs")

    args = parser.parse_args()


    TranscriptionGenerator(args.videos, args.transcription_jsons_dir).transcribe()
    VideoTranscoder(args.videos, args.transcoded_videos_dir).transcode()

    # pass transcriptions to elastic
    # split two paths to be async


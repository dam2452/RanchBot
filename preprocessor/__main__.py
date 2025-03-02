import argparse

from transciption_generator import TranscriptionGenerator
from video_transcoder import VideoTranscoder


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("videos", type=argparse.FileType("r"), help="Path to input videos for preprocessing")
    parser.add_argument("--transcoded-videos-dir", "-v", type=argparse.FileType("w"), default="transcoded_videos", help="Path for output videos after transcoding")
    parser.add_argument("--transcription-jsons-dir", "-j", type=argparse.FileType("w"), default="transcriptions", help="Path for output transcriptions JSONs")


    args = parser.parse_args()

    TranscriptionGenerator(args.videos, args.transcription_jsons_dir).transcribe()
    VideoTranscoder(args.videos, args.transcoded_videos_dir).transcode()

    # pass transcriptions to elastic
    # split two paths to be async

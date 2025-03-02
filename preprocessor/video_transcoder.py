from pathlib import Path

class VideoTranscoder:
    def __init__(self, input_videos: Path, output_videos: Path):
        self.__input_videos = input_videos
        self.__output_videos = output_videos

    def transcode(self):
        self.__prepare_videos()
        self.__do_transcoding()

    def __prepare_videos(self) -> None:
        pass

    def __do_transcoding(self) -> None:
        pass
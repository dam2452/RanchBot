from pathlib import Path

class VideoTranscoder:
    DEFAULT_CODEC: str = "h264_nvenc"
    DEFAULT_PRESET: str = "slow"
    DEFAULT_CRF: int = 31
    DEFAULT_GOP_SIZE: float = 0.5

    def __init__(
            self,
            input_videos: Path,
            output_videos: Path,
            codec: str = DEFAULT_CODEC,
            preset: str = DEFAULT_PRESET,
            crf: int = DEFAULT_CRF,
            gop_size: float = DEFAULT_GOP_SIZE,
    ):
        self.__input_videos = input_videos
        self.__output_videos = output_videos

        self.__codec = codec
        self.__preset = preset
        self.__crf = crf
        self.__gop_size = gop_size


        # video converter

    def transcode(self):
        self.__prepare_videos()
        self.__do_transcoding()

    def __prepare_videos(self) -> None:
        pass

    def __do_transcoding(self) -> None:
        pass
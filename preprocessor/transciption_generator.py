from pathlib import Path


class TranscriptionGenerator:
    def __init__(self, input_videos: Path, output_jsons: Path):
        self.__input_videos = input_videos
        self.__output_jsons = output_jsons

        # normalizer -> audio processor -> json processor

    def transcribe(self) -> None:
        self.__get_best_audio_path()
        self.__normalize()
        self.__do_transcribe()
        self.__dump_json()
        self.__format_json()

    def __get_best_audio_path(self) -> None:
        pass

    def __normalize(self) -> None:
        pass

    def __do_transcribe(self) -> None:
        pass

    def __dump_json(self) -> None:
        pass

    def __format_json(self) -> None:
        pass

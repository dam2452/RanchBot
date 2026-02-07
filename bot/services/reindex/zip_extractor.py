import io
import json
import logging
from pathlib import Path
import zipfile


class ZipExtractor:
    def __init__(self, logger: logging.Logger):
        self.__logger = logger

    def extract_to_memory(self, zip_path: Path) -> dict[str, io.BytesIO]:
        extracted_files = {}

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for file_info in zf.infolist():
                    if not file_info.filename.endswith('.jsonl'):
                        continue

                    content = zf.read(file_info.filename)
                    buffer = io.BytesIO(content)

                    jsonl_type = self.__detect_type_from_filename(file_info.filename)
                    if jsonl_type:
                        extracted_files[jsonl_type] = buffer

        except zipfile.BadZipFile as e:
            self.__logger.error(f"Corrupted zip file: {zip_path}")
            raise ValueError(f"Invalid zip file: {zip_path}") from e

        return extracted_files

    def parse_jsonl_from_memory(self, buffer: io.BytesIO) -> list[dict]:
        documents = []
        buffer.seek(0)

        for line in buffer:
            line_str = line.decode('utf-8').strip()
            if line_str:
                try:
                    doc = json.loads(line_str)
                    documents.append(doc)
                except json.JSONDecodeError as e:
                    self.__logger.warning(f"Failed to parse JSONL line: {e}")

        return documents

    def __detect_type_from_filename(self, filename: str) -> str:
        if 'text_segments' in filename:
            return 'text_segments'
        if 'text_embeddings' in filename:
            return 'text_embeddings'
        if 'video_frames' in filename:
            return 'video_frames'
        if 'episode_name' in filename:
            return 'episode_names'
        if 'full_episode_embedding' in filename:
            return 'full_episode_embeddings'
        if 'sound_event_embeddings' in filename:
            return 'sound_event_embeddings'
        if 'sound_events' in filename:
            return 'sound_events'
        return None

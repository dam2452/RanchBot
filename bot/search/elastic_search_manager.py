import json

from elasticsearch import (
    AsyncElasticsearch,
    exceptions as es_exceptions,
)
import urllib3

from bot.settings import settings as s
from bot.utils.log import Logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ElasticSearchManager:
    INDEX_MAPPING: json = {
        "mappings": {
            "properties": {
                "episode_info": {
                    "type": "object",
                    "properties": {
                        "season": {"type": "integer"},
                        "episode_number": {"type": "integer"},
                        "title": {"type": "text"},
                        "premiere_date": {"type": "date", "format": "yyyy-MM-dd"},
                        "viewership": {"type": "integer"},
                        "description": {"type": "text"},
                        "summary": {"type": "text"},
                        "is_special_feature": {"type": "boolean"},
                        "special_feature_type": {"type": "keyword"},
                    },
                },
                "text": {"type": "text"},
                "start": {"type": "float"},
                "end": {"type": "float"},
                "video_path": {"type": "keyword"},
                "transcription": {
                    "type": "object",
                    "properties": {
                        "format": {"type": "keyword"},
                        "source_file": {"type": "keyword"},
                        "language_code": {"type": "keyword"},
                        "language_probability": {"type": "float"},
                        "segments": {
                            "type": "nested",
                            "properties": {
                                "id": {"type": "integer"},
                                "start": {"type": "float"},
                                "end": {"type": "float"},
                                "text": {"type": "text"},
                                "speaker": {"type": "keyword"},
                                "words": {"type": "object", "enabled": False},
                            },
                        },
                    },
                },
                "scene_timestamps": {
                    "type": "object",
                    "properties": {
                        "total_scenes": {"type": "integer"},
                        "video_info": {
                            "type": "object",
                            "properties": {
                                "fps": {"type": "float"},
                                "duration": {"type": "float"},
                                "total_frames": {"type": "integer"},
                            },
                        },
                        "detection_settings": {"type": "object", "enabled": False},
                        "scenes": {
                            "type": "nested",
                            "properties": {
                                "scene_number": {"type": "integer"},
                                "start": {"type": "object", "enabled": False},
                                "end": {"type": "object", "enabled": False},
                                "duration": {"type": "float"},
                                "frame_count": {"type": "integer"},
                            },
                        },
                    },
                },
                "text_embeddings": {
                    "type": "nested",
                    "properties": {
                        "segment_range": {"type": "integer"},
                        "text": {"type": "text"},
                        "embedding": {"type": "float", "index": False},
                    },
                },
                "video_embeddings": {
                    "type": "nested",
                    "properties": {
                        "frame_number": {"type": "integer"},
                        "timestamp": {"type": "float"},
                        "type": {"type": "keyword"},
                        "embedding": {"type": "float", "index": False},
                    },
                },
                "id": {"type": "integer"},
                "seek": {"type": "integer"},
                "author": {"type": "keyword"},
                "comment": {"type": "text"},
                "tags": {"type": "keyword"},
                "location": {"type": "keyword"},
                "actors": {"type": "keyword"},
            },
        },
    }

    @staticmethod
    async def connect_to_elasticsearch(logger: Logger) -> AsyncElasticsearch:
        es = AsyncElasticsearch(
            hosts=[s.ES_HOST],
            basic_auth=(s.ES_USER, s.ES_PASS.get_secret_value()),
            verify_certs=False,
        )
        try:
            if not await es.ping():
                raise es_exceptions.ConnectionError("Failed to connect to Elasticsearch.")
            logger.info( "Connected to Elasticsearch.")
            return es
        except es_exceptions.ConnectionError as e:
            logger.info( f"Connection error: {str(e)}")
            raise

import json

from elasticsearch import (
    AsyncElasticsearch,
    exceptions as es_exceptions,
)
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# pylint: disable=duplicate-code
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
                        "premiere_date": {"type": "date", "format": "dd.MM.yyyy||d.MM.yyyy||d.M.yyyy||yyyy-MM-dd||strict_date_optional_time||epoch_millis"},
                        "viewership": {"type": "keyword"},
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

    SEGMENTS_INDEX_MAPPING: json = {
        "mappings": {
            "properties": {
                "episode_id": {"type": "keyword"},
                "episode_metadata": {
                    "properties": {
                        "season": {"type": "integer"},
                        "episode_number": {"type": "integer"},
                        "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                        "premiere_date": {"type": "date", "format": "dd.MM.yyyy||d.MM.yyyy||d.M.yyyy||yyyy-MM-dd||strict_date_optional_time||epoch_millis"},
                        "series_name": {"type": "keyword"},
                        "viewership": {"type": "keyword"},
                    },
                },
                "segment_id": {"type": "integer"},
                "text": {
                    "type": "text",
                    "analyzer": "standard",
                    "fields": {
                        "keyword": {"type": "keyword"},
                    },
                },
                "start_time": {"type": "float"},
                "end_time": {"type": "float"},
                "speaker": {"type": "keyword"},
                "video_path": {"type": "keyword"},
                "scene_info": {
                    "properties": {
                        "scene_number": {"type": "integer"},
                        "scene_start_time": {"type": "float"},
                        "scene_end_time": {"type": "float"},
                        "scene_start_frame": {"type": "integer"},
                        "scene_end_frame": {"type": "integer"},
                    },
                },
            },
        },
    }

    TEXT_EMBEDDINGS_INDEX_MAPPING: json = {
        "mappings": {
            "properties": {
                "episode_id": {"type": "keyword"},
                "episode_metadata": {
                    "properties": {
                        "season": {"type": "integer"},
                        "episode_number": {"type": "integer"},
                        "title": {"type": "text"},
                        "premiere_date": {"type": "date", "format": "dd.MM.yyyy||d.MM.yyyy||d.M.yyyy||yyyy-MM-dd||strict_date_optional_time||epoch_millis"},
                        "series_name": {"type": "keyword"},
                    },
                },
                "embedding_id": {"type": "integer"},
                "segment_range": {"type": "integer"},
                "text": {"type": "text"},
                "text_embedding": {
                    "type": "dense_vector",
                    "dims": 1536,
                    "index": True,
                    "similarity": "cosine",
                },
                "video_path": {"type": "keyword"},
            },
        },
    }

    VIDEO_EMBEDDINGS_INDEX_MAPPING: json = {
        "mappings": {
            "properties": {
                "episode_id": {"type": "keyword"},
                "episode_metadata": {
                    "properties": {
                        "season": {"type": "integer"},
                        "episode_number": {"type": "integer"},
                        "title": {"type": "text"},
                        "premiere_date": {"type": "date", "format": "dd.MM.yyyy||d.MM.yyyy||d.M.yyyy||yyyy-MM-dd||strict_date_optional_time||epoch_millis"},
                        "series_name": {"type": "keyword"},
                    },
                },
                "frame_number": {"type": "integer"},
                "timestamp": {"type": "float"},
                "frame_type": {"type": "keyword"},
                "scene_number": {"type": "integer"},
                "video_embedding": {
                    "type": "dense_vector",
                    "dims": 1536,
                    "index": True,
                    "similarity": "cosine",
                },
                "perceptual_hash": {"type": "keyword"},
                "perceptual_hash_int": {"type": "unsigned_long"},
                "video_path": {"type": "keyword"},
                "character_appearances": {"type": "keyword"},
                "detected_objects": {
                    "type": "nested",
                    "properties": {
                        "class": {"type": "keyword"},
                        "count": {"type": "integer"},
                    },
                },
                "scene_info": {
                    "properties": {
                        "scene_start_time": {"type": "float"},
                        "scene_end_time": {"type": "float"},
                        "scene_start_frame": {"type": "integer"},
                        "scene_end_frame": {"type": "integer"},
                    },
                },
            },
        },
    }

    EPISODE_NAMES_INDEX_MAPPING: json = {
        "mappings": {
            "properties": {
                "episode_id": {"type": "keyword"},
                "episode_metadata": {
                    "properties": {
                        "season": {"type": "integer"},
                        "episode_number": {"type": "integer"},
                        "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                        "premiere_date": {"type": "date", "format": "dd.MM.yyyy||d.MM.yyyy||d.M.yyyy||yyyy-MM-dd||strict_date_optional_time||epoch_millis"},
                        "series_name": {"type": "keyword"},
                        "viewership": {"type": "keyword"},
                    },
                },
                "title": {
                    "type": "text",
                    "analyzer": "standard",
                    "fields": {
                        "keyword": {"type": "keyword"},
                    },
                },
                "title_embedding": {
                    "type": "dense_vector",
                    "dims": 1536,
                    "index": True,
                    "similarity": "cosine",
                },
                "video_path": {"type": "keyword"},
            },
        },
    }

    @staticmethod
    async def connect_to_elasticsearch(
        es_host: str,
        es_user: str,
        es_pass: str,
        logger,
    ) -> AsyncElasticsearch:
        es_config = {
            "hosts": [es_host],
            "verify_certs": False,
        }

        if es_user and es_pass:
            es_config["basic_auth"] = (es_user, es_pass)

        es = AsyncElasticsearch(**es_config)
        try:
            if not await es.ping():
                raise es_exceptions.ConnectionError("Failed to connect to Elasticsearch.")
            logger.info("Connected to Elasticsearch.")
            return es
        except es_exceptions.ConnectionError as e:
            logger.info(f"Connection error: {str(e)}")
            raise
# pylint: enable=duplicate-code

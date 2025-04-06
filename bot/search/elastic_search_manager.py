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
                "episode_info": {"type": "object"},
                "text": {"type": "text"},
                "start": {"type": "float"},
                "end": {"type": "float"},
                "video_path": {"type": "keyword"},
            },
        },
    }

    @staticmethod
    async def connect_to_elasticsearch(logger: Logger) -> AsyncElasticsearch:
        es = AsyncElasticsearch(
            hosts=[s.ES_HOST],
            basic_auth=(s.ES_USER, s.ES_PASS),
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

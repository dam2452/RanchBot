from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from elasticsearch import AsyncElasticsearch
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ElasticsearchWrapper:

    def __init__(self, index_name: str, host: str='localhost:9200', dry_run: bool=False) -> None:
        self.index_name: str = index_name
        self.host: str = host
        self.dry_run: bool = dry_run
        self._client: Optional[AsyncElasticsearch] = None

    async def _get_client(self) -> AsyncElasticsearch:
        if self._client is None:
            self._client = AsyncElasticsearch([self.host], verify_certs=False, ssl_show_warn=False)
        return self._client

    async def index_exists(self) -> bool:
        if self.dry_run:
            return False
        client = await self._get_client()
        return await client.indices.exists(index=self.index_name)

    async def create_index(self, mapping: Dict[str, Any]) -> None:
        if self.dry_run:
            return
        client = await self._get_client()
        await client.indices.create(index=self.index_name, body=mapping)

    async def delete_index(self) -> None:
        if self.dry_run:
            return
        client = await self._get_client()
        await client.indices.delete(index=self.index_name, ignore=[404])

    async def bulk_index(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        if self.dry_run:
            return {'indexed': len(documents), 'errors': []}
        client = await self._get_client()
        actions = []
        for doc in documents:
            actions.append({'index': {'_index': self.index_name}})
            actions.append(doc)
        try:
            response = await client.bulk(operations=actions)
            return response
        except Exception as e:
            return {'errors': str(e)}

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

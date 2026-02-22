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
    def __init__(
            self,
            index_name: str,
            host: str = 'localhost:9200',
            dry_run: bool = False,
    ) -> None:
        self.__index_name = index_name
        self.__host = host
        self.__dry_run = dry_run
        self.__client: Optional[AsyncElasticsearch] = None

    @property
    def index_name(self) -> str:
        return self.__index_name

    async def bulk_index(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        if self.__dry_run:
            return {'indexed': len(documents), 'errors': []}

        client = await self.__ensure_client()
        actions = self.__build_bulk_actions(documents)

        try:
            response = await client.bulk(operations=actions)
            return response
        except Exception as e:
            return {'errors': [str(e)]}

    async def create_index(self, mapping: Dict[str, Any]) -> None:
        if self.__dry_run:
            return

        client = await self.__ensure_client()
        await client.indices.create(index=self.__index_name, body=mapping)

    async def delete_index(self) -> None:
        if self.__dry_run:
            return

        client = await self.__ensure_client()
        if await client.indices.exists(index=self.__index_name):
            await client.indices.delete(index=self.__index_name)

    async def index_exists(self) -> bool:
        if self.__dry_run:
            return False

        client = await self.__ensure_client()
        return await client.indices.exists(index=self.__index_name)

    async def close(self) -> None:
        if self.__client is not None:
            await self.__client.close()
            self.__client = None

    async def __ensure_client(self) -> AsyncElasticsearch:
        if self.__client is None:
            self.__client = AsyncElasticsearch(
                [self.__host],
                verify_certs=False,
                ssl_show_warn=False,
            )
        return self.__client

    def __build_bulk_actions(self, documents: List[Dict[str, Any]]) -> List[Any]:
        actions = []
        for doc in documents:
            actions.append({'index': {'_index': self.__index_name}})
            actions.append(doc)
        return actions

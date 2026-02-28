from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from elasticsearch import AsyncElasticsearch

from preprocessor.services.search.clients.embedding_service import EmbeddingService


class ElasticsearchQueries:
    def __init__(self, embedding_service: EmbeddingService, index_base: str) -> None:
        self.__embedding_service = embedding_service
        self.__index_base = index_base

    async def get_stats(self, es_client: AsyncElasticsearch) -> Dict[str, int]:
        return {
            'segments': (await es_client.count(index=self.__segments_index))['count'],
            'text_embeddings': (await es_client.count(index=self.__text_embeddings_index))['count'],
            'video_embeddings': (await es_client.count(index=self.__video_frames_index))['count'],
            'episode_names': (await es_client.count(index=self.__episode_names_index))['count'],
        }

    async def list_characters(self, es_client: AsyncElasticsearch) -> List[Tuple[str, int]]:
        return await self.__list_nested_terms(es_client, self.__video_frames_index, 'character_appearances', 'name')

    async def list_objects(self, es_client: AsyncElasticsearch) -> List[Tuple[str, int]]:
        return await self.__list_nested_terms(es_client, self.__video_frames_index, 'detected_objects', 'class')

    async def search_by_emotion(
            self,
            es_client: AsyncElasticsearch,
            emotion: str,
            season: Optional[int] = None,
            episode: Optional[int] = None,
            character: Optional[str] = None,
            limit: int = 20,
    ) -> Dict[str, Any]:
        nested_must = [{'term': {'character_appearances.emotion.label': emotion}}]
        if character:
            nested_must.append({'term': {'character_appearances.name': character}})

        must_clauses = [{'nested': {'path': 'character_appearances', 'query': {'bool': {'must': nested_must}}}}]
        must_clauses.extend(self.__build_episode_filters(season, episode))

        nested_filter = self.__build_nested_filter(emotion, character)

        return await es_client.search(
            index=self.__video_frames_index,
            query={'bool': {'must': must_clauses}},
            sort=[{
                'character_appearances.emotion.confidence': {
                    'order': 'desc',
                    'nested': {'path': 'character_appearances', 'filter': nested_filter},
                },
            }],
            track_scores=True,
            size=limit,
            _source=[
                'episode_id', 'frame_number', 'timestamp', 'video_path',
                'episode_metadata', 'character_appearances', 'scene_info',
            ],
        )

    async def search_video_semantic(
            self,
            es_client: AsyncElasticsearch,
            image_path: str,
            season: Optional[int] = None,
            episode: Optional[int] = None,
            character: Optional[str] = None,
            limit: int = 10,
    ) -> Dict[str, Any]:
        embedding = self.__embedding_service.get_image_embedding(image_path)
        return await self.__execute_knn_query(
            es_client, self.__video_frames_index, 'video_embedding', embedding,
            limit, season, episode, character,
        )

    async def __execute_knn_query(
            self, es_client: AsyncElasticsearch, index: str, field: str, vector: List[float],
            limit: int, season: Optional[int], episode: Optional[int], character: Optional[str] = None,
    ) -> Dict[str, Any]:
        filters = self.__build_episode_filters(season, episode)
        if character:
            filters.append({
                'nested': {
                    'path': 'character_appearances',
                    'query': {'term': {'character_appearances.name': character}},
                },
            })

        knn = {
            'field': field,
            'query_vector': vector,
            'k': limit,
            'num_candidates': limit * 10,
            'filter': filters if filters else None,
        }
        return await es_client.search(index=index, knn=knn, size=limit)

    @staticmethod
    def __build_episode_filters(season: Optional[int], episode: Optional[int]) -> List[Dict[str, Any]]:
        filters = []
        if season is not None:
            filters.append({'term': {'episode_metadata.season': season}})
        if episode is not None:
            filters.append({'term': {'episode_metadata.episode_number': episode}})
        return filters

    @staticmethod
    def __build_nested_filter(emotion: str, character: Optional[str]) -> Dict[str, Any]:
        if not character:
            return {'term': {'character_appearances.emotion.label': emotion}}
        return {
            'bool': {
                'must': [
                    {'term': {'character_appearances.emotion.label': emotion}},
                    {'term': {'character_appearances.name': character}},
                ],
            },
        }

    @staticmethod
    async def __list_nested_terms(es_client: AsyncElasticsearch, index: str, path: str, field: str) -> List[
        Tuple[str, int]
    ]:
        result = await es_client.search(
            index=index,
            size=0,
            aggs={
                'nested_path': {
                    'nested': {'path': path},
                    'aggs': {
                        'terms_agg': {'terms': {'field': f'{path}.{field}', 'size': 1000}},
                    },
                },
            },
        )
        buckets = result['aggregations']['nested_path']['terms_agg']['buckets']
        return [(b['key'], b['doc_count']) for b in buckets]

    @property
    def __episode_names_index(self) -> str:
        return f'{self.__index_base}_episode_names'

    @property
    def __segments_index(self) -> str:
        return f'{self.__index_base}_text_segments'

    @property
    def __text_embeddings_index(self) -> str:
        return f'{self.__index_base}_text_embeddings'

    @property
    def __video_frames_index(self) -> str:
        return f'{self.__index_base}_video_frames'

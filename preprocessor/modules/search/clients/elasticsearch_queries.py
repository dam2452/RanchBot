from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from elasticsearch import AsyncElasticsearch

from preprocessor.modules.search.clients.embedding_service import EmbeddingService


class ElasticsearchQueries:

    def __init__(self, embedding_service: EmbeddingService, index_base: str) -> None:
        self._embedding_service = embedding_service
        self._index_base = index_base

    async def get_stats(self, es_client: AsyncElasticsearch) -> Dict[str, int]:
        return {
            'segments': (await es_client.count(index=self.__segments_index))['count'],
            'text_embeddings': (await es_client.count(index=self.__text_embeddings_index))['count'],
            'video_embeddings': (await es_client.count(index=self.__video_frames_index))['count'],
            'episode_names': (await es_client.count(index=self.__episode_names_index))['count'],
        }

    async def list_characters(self, es_client: AsyncElasticsearch) -> List[Tuple[str, int]]:
        result = await es_client.search(
            index=self.__video_frames_index,
            size=0,
            aggs={
                'characters_nested': {
                    'nested': {'path': 'character_appearances'},
                    'aggs': {
                        'character_names': {
                            'terms': {'field': 'character_appearances.name', 'size': 1000},
                        },
                    },
                },
            },
        )
        buckets = result['aggregations']['characters_nested']['character_names']['buckets']
        return [(b['key'], b['doc_count']) for b in buckets]

    async def list_objects(self, es_client: AsyncElasticsearch) -> List[Tuple[str, int]]:
        result = await es_client.search(
            index=self.__video_frames_index,
            size=0,
            aggs={
                'objects_nested': {
                    'nested': {'path': 'detected_objects'},
                    'aggs': {
                        'object_classes': {
                            'terms': {'field': 'detected_objects.class', 'size': 1000},
                        },
                    },
                },
            },
        )
        buckets = result['aggregations']['objects_nested']['object_classes']['buckets']
        return [(b['key'], b['doc_count']) for b in buckets]

    async def search_by_character(
        self,
        es_client: AsyncElasticsearch,
        character: str,
        season: Optional[int]=None,
        episode: Optional[int]=None,
        limit: int=20,
    ) -> Dict[str, Any]:
        must_clauses = [{
            'nested': {
                'path': 'character_appearances',
                'query': {'term': {'character_appearances.name': character}},
            },
        }]
        must_clauses.extend(self.__build_episode_filters(season, episode))
        return await es_client.search(
            index=self.__video_frames_index,
            query={'bool': {'must': must_clauses}},
            size=limit,
            _source=[
                'episode_id', 'frame_number', 'timestamp', 'video_path',
                'episode_metadata', 'character_appearances', 'scene_info',
            ],
        )

    async def search_by_emotion(
        self,
        es_client: AsyncElasticsearch,
        emotion: str,
        season: Optional[int]=None,
        episode: Optional[int]=None,
        character: Optional[str]=None,
        limit: int=20,
    ) -> Dict[str, Any]:
        nested_must = [{'term': {'character_appearances.emotion.label': emotion}}]
        if character:
            nested_must.append({'term': {'character_appearances.name': character}})
        must_clauses = [{'nested': {'path': 'character_appearances', 'query': {'bool': {'must': nested_must}}}}]
        must_clauses.extend(self.__build_episode_filters(season, episode))
        nested_filter: Dict[str, Any] = {'term': {'character_appearances.emotion.label': emotion}}
        if character:
            nested_filter = {
                'bool': {
                    'must': [
                        {'term': {'character_appearances.emotion.label': emotion}},
                        {'term': {'character_appearances.name': character}},
                    ],
                },
            }
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

    async def search_by_object(
        self,
        es_client: AsyncElasticsearch,
        object_query: str,
        season: Optional[int]=None,
        episode: Optional[int]=None,
        limit: int=20,
    ) -> Dict[str, Any]:
        filter_clauses = self.__build_episode_filters(season, episode)
        must_clauses: List[Dict[str, Any]] = []
        if ':' in object_query:
            object_class, count_filter = object_query.split(':', 1)
            object_class = object_class.strip()
            if count_filter.endswith('+'):
                min_count = int(count_filter[:-1])
                must_clauses.append({
                    'nested': {
                        'path': 'detected_objects',
                        'query': {
                            'bool': {
                                'must': [
                                    {'term': {'detected_objects.class': object_class}},
                                    {'range': {'detected_objects.count': {'gte': min_count}}},
                                ],
                            },
                        },
                    },
                })
            elif '-' in count_filter:
                min_c, max_c = count_filter.split('-')
                must_clauses.append({
                    'nested': {
                        'path': 'detected_objects',
                        'query': {
                            'bool': {
                                'must': [
                                    {'term': {'detected_objects.class': object_class}},
                                    {'range': {'detected_objects.count': {'gte': int(min_c), 'lte': int(max_c)}}},
                                ],
                            },
                        },
                    },
                })
            else:
                exact_count = int(count_filter)
                must_clauses.append({
                    'nested': {
                        'path': 'detected_objects',
                        'query': {
                            'bool': {
                                'must': [
                                    {'term': {'detected_objects.class': object_class}},
                                    {'term': {'detected_objects.count': exact_count}},
                                ],
                            },
                        },
                    },
                })
        else:
            must_clauses.append({
                'nested': {
                    'path': 'detected_objects',
                    'query': {'term': {'detected_objects.class': object_query.strip()}},
                },
            })
        query_body = {'bool': {'must': must_clauses, 'filter': filter_clauses}}
        object_class = object_query.split(':')[0].strip() if ':' in object_query else object_query.strip()
        return await es_client.search(
            index=self.__video_frames_index,
            query=query_body,
            sort=[{
                'detected_objects.count': {
                    'order': 'desc',
                    'nested': {
                        'path': 'detected_objects',
                        'filter': {'term': {'detected_objects.class': object_class}},
                    },
                },
            }],
            track_scores=True,
            size=limit,
            _source=[
                'episode_id', 'frame_number', 'timestamp', 'detected_objects', 'character_appearances',
                'video_path', 'episode_metadata', 'scene_info',
            ],
        )

    async def search_episode_name(
        self,
        es_client: AsyncElasticsearch,
        query: str,
        season: Optional[int]=None,
        limit: int=20,
    ) -> Dict[str, Any]:
        must_clauses = [
            {'multi_match': {'query': query, 'fields': ['title^2', 'episode_metadata.title'], 'fuzziness': 'AUTO'}},
        ]
        if season is not None:
            must_clauses.append({'term': {'episode_metadata.season': season}})
        query_body = {'bool': {'must': must_clauses}}
        return await es_client.search(
            index=self.__episode_names_index,
            query=query_body,
            size=limit,
            _source=['episode_id', 'title', 'video_path', 'episode_metadata'],
        )

    async def search_episode_name_semantic(
        self,
        es_client: AsyncElasticsearch,
        text: str,
        season: Optional[int]=None,
        limit: int=10,
    ) -> Dict[str, Any]:
        embedding = self._embedding_service.get_text_embedding(text)
        filter_clauses = []
        if season is not None:
            filter_clauses.append({'term': {'episode_metadata.season': season}})
        knn_query: Dict[str, Any] = {
            'field': 'title_embedding',
            'query_vector': embedding,
            'k': limit,
            'num_candidates': limit * 10,
        }
        if filter_clauses:
            knn_query['filter'] = filter_clauses
        return await es_client.search(
            index=self.__episode_names_index,
            knn=knn_query,
            size=limit,
            _source=['episode_id', 'title', 'video_path', 'episode_metadata'],
        )

    async def search_perceptual_hash(
        self,
        es_client: AsyncElasticsearch,
        phash: str,
        limit: int=10,
    ) -> Dict[str, Any]:
        return await es_client.search(
            index=self.__video_frames_index,
            query={'term': {'perceptual_hash': phash}},
            size=limit,
            _source=[
                'episode_id', 'frame_number', 'timestamp', 'video_path',
                'episode_metadata', 'perceptual_hash', 'scene_info',
            ],
        )

    async def search_text_query(
        self,
        es_client: AsyncElasticsearch,
        query: str,
        season: Optional[int]=None,
        episode: Optional[int]=None,
        limit: int=20,
    ) -> Dict[str, Any]:
        must_clauses = [
            {'multi_match': {'query': query, 'fields': ['text^2', 'episode_metadata.title'], 'fuzziness': 'AUTO'}},
        ]
        must_clauses.extend(self.__build_episode_filters(season, episode))
        query_body = {'bool': {'must': must_clauses}}
        return await es_client.search(
            index=self.__segments_index,
            query=query_body,
            size=limit,
            _source=[
                'episode_id', 'segment_id', 'text', 'start_time', 'end_time', 'speaker',
                'video_path', 'episode_metadata', 'scene_info',
            ],
        )

    async def search_text_semantic(
        self,
        es_client: AsyncElasticsearch,
        text: str,
        season: Optional[int]=None,
        episode: Optional[int]=None,
        limit: int=10,
    ) -> Dict[str, Any]:
        embedding = self._embedding_service.get_text_embedding(text)
        filter_clauses = self.__build_episode_filters(season, episode)
        knn_query: Dict[str, Any] = {
            'field': 'text_embedding',
            'query_vector': embedding,
            'k': limit,
            'num_candidates': limit * 10,
        }
        if filter_clauses:
            knn_query['filter'] = filter_clauses
        return await es_client.search(
            index=self.__text_embeddings_index,
            knn=knn_query,
            size=limit,
            _source=[
                'episode_id', 'embedding_id', 'text', 'segment_range',
                'video_path', 'episode_metadata', 'scene_info',
            ],
        )

    async def search_text_to_video(
        self,
        es_client: AsyncElasticsearch,
        text: str,
        season: Optional[int]=None,
        episode: Optional[int]=None,
        character: Optional[str]=None,
        limit: int=10,
    ) -> Dict[str, Any]:
        embedding = self._embedding_service.get_text_embedding(text)
        filter_clauses = self.__build_episode_filters(season, episode)
        if character:
            filter_clauses.append({
                'nested': {
                    'path': 'character_appearances',
                    'query': {'term': {'character_appearances.name': character}},
                },
            })
        knn_query: Dict[str, Any] = {
            'field': 'video_embedding',
            'query_vector': embedding,
            'k': limit,
            'num_candidates': limit * 10,
        }
        if filter_clauses:
            knn_query['filter'] = filter_clauses
        return await es_client.search(
            index=self.__video_frames_index,
            knn=knn_query,
            size=limit,
            _source=[
                'episode_id', 'frame_number', 'timestamp', 'frame_type', 'scene_number',
                'perceptual_hash', 'video_path', 'episode_metadata', 'character_appearances', 'scene_info',
            ],
        )

    async def search_video_semantic(
        self,
        es_client: AsyncElasticsearch,
        image_path: str,
        season: Optional[int]=None,
        episode: Optional[int]=None,
        character: Optional[str]=None,
        limit: int=10,
    ) -> Dict[str, Any]:
        embedding = self._embedding_service.get_image_embedding(image_path)
        filter_clauses = self.__build_episode_filters(season, episode)
        if character:
            filter_clauses.append({
                'nested': {
                    'path': 'character_appearances',
                    'query': {'term': {'character_appearances.name': character}},
                },
            })
        knn_query: Dict[str, Any] = {
            'field': 'video_embedding',
            'query_vector': embedding,
            'k': limit,
            'num_candidates': limit * 10,
        }
        if filter_clauses:
            knn_query['filter'] = filter_clauses
        return await es_client.search(
            index=self.__video_frames_index,
            knn=knn_query,
            size=limit,
            _source=[
                'episode_id', 'frame_number', 'timestamp', 'frame_type', 'scene_number',
                'perceptual_hash', 'video_path', 'episode_metadata', 'character_appearances', 'scene_info',
            ],
        )

    @staticmethod
    def __build_episode_filters(season: Optional[int], episode: Optional[int]) -> List[Dict[str, Any]]:
        filters = []
        if season is not None:
            filters.append({'term': {'episode_metadata.season': season}})
        if episode is not None:
            filters.append({'term': {'episode_metadata.episode_number': episode}})
        return filters

    @property
    def __episode_names_index(self) -> str:
        return f'{self._index_base}_episode_names'

    @property
    def __segments_index(self) -> str:
        return f'{self._index_base}_text_segments'

    @property
    def __text_embeddings_index(self) -> str:
        return f'{self._index_base}_text_embeddings'

    @property
    def __video_frames_index(self) -> str:
        return f'{self._index_base}_video_frames'

import asyncio
import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from preprocessor.config.step_configs import ElasticsearchConfig
from preprocessor.core.artifacts import (
    ElasticDocuments,
    IndexingResult,
)
from preprocessor.core.base_step import PipelineStep
from preprocessor.core.context import ExecutionContext
from preprocessor.services.search.elasticsearch import ElasticsearchWrapper


class ElasticsearchIndexerStep(PipelineStep[List[ElasticDocuments], IndexingResult, ElasticsearchConfig]):

    def __init__(self, config: ElasticsearchConfig) -> None:
        super().__init__(config)
        self._es: Optional[ElasticsearchWrapper] = None

    def cleanup(self) -> None:
        if self._es:
            asyncio.run(self._es.close())
            self._es = None

    def execute(self, input_data: List[ElasticDocuments], context: ExecutionContext) -> IndexingResult:
        return asyncio.run(self._execute_async(input_data, context))

    @property
    def name(self) -> str:
        return 'elasticsearch_indexing'

    async def _execute_async(
        self,
        input_data: List[ElasticDocuments],
        context: ExecutionContext,
    ) -> IndexingResult:
        if not input_data:
            return await self._create_empty_result(context)

        docs_by_type = self._group_documents_by_type(input_data)
        total_indexed = await self._index_all_document_types(docs_by_type, context)

        return IndexingResult(
            index_name=self.config.index_name,
            document_count=total_indexed,
            success=True,
        )

    async def _create_empty_result(self, context: ExecutionContext) -> IndexingResult:
        context.logger.warning('No documents to index.')
        return IndexingResult(
            index_name=self.config.index_name,
            document_count=0,
            success=True,
        )

    @staticmethod
    def _group_documents_by_type(input_data: List[ElasticDocuments]) -> Dict[str, List[Path]]:
        docs_by_type: Dict[str, List[Path]] = {}
        for doc_artifact in input_data:
            doc_type: str = doc_artifact.path.parent.name
            if doc_type not in docs_by_type:
                docs_by_type[doc_type] = []
            docs_by_type[doc_type].append(doc_artifact.path)
        return docs_by_type

    async def _index_all_document_types(
        self,
        docs_by_type: Dict[str, List[Path]],
        context: ExecutionContext,
    ) -> int:
        total_indexed: int = 0
        for doc_type, paths in docs_by_type.items():
            try:
                indexed_count = await self._index_document_type(doc_type, paths, context)
                total_indexed += indexed_count
            except Exception as e:
                context.logger.error(f'Elasticsearch indexing failed for {doc_type}: {e}')
                raise
        return total_indexed

    async def _index_document_type(
        self,
        doc_type: str,
        paths: List[Path],
        context: ExecutionContext,
    ) -> int:
        index_name: str = f'{self.config.index_name}_{doc_type}'
        context.logger.info(f'Indexing {len(paths)} files into {index_name}')

        await self._ensure_elasticsearch_wrapper(index_name)
        await self._prepare_index(doc_type)

        documents = self._load_documents_from_paths(paths)
        return await self._bulk_index_documents(documents, index_name, context)

    async def _ensure_elasticsearch_wrapper(self, index_name: str) -> None:
        if self._es is None or self._es.index_name != index_name:
            if self._es is not None:
                await self._es.close()
            self._es = ElasticsearchWrapper(
                index_name=index_name,
                host=self.config.host,
                dry_run=self.config.dry_run,
            )

    async def _prepare_index(self, doc_type: str) -> None:
        if not self.config.append:
            await self._es.delete_index()

        mapping: Optional[Dict[str, Any]] = self.__get_mapping_for_type(doc_type)
        if mapping:
            await self._es.create_index(mapping)

    @staticmethod
    def _load_documents_from_paths(paths: List[Path]) -> List[Dict[str, Any]]:
        documents: List[Dict[str, Any]] = []
        for path in paths:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        documents.append(json.loads(line))
        return documents

    async def _bulk_index_documents(
        self,
        documents: List[Dict[str, Any]],
        index_name: str,
        context: ExecutionContext,
    ) -> int:
        if not documents:
            return 0

        if not self.config.dry_run:
            await self._es.bulk_index(documents)
            return len(documents)

        context.logger.info(
            f'Dry-run: would index {len(documents)} docs to {index_name}',
        )
        return 0

    @staticmethod
    def __get_mapping_for_type(
        doc_type: str,  # pylint: disable=unused-argument
    ) -> Optional[Dict[str, Any]]:
        return None

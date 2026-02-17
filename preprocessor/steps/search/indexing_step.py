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


class ElasticsearchIndexerStep(
    PipelineStep[List[ElasticDocuments], IndexingResult, ElasticsearchConfig],
):
    def __init__(self, config: ElasticsearchConfig) -> None:
        super().__init__(config)
        self.__es: Optional[ElasticsearchWrapper] = None

    @property
    def is_global(self) -> bool:
        return True

    @property
    def supports_batch_processing(self) -> bool:
        return True

    @property
    def uses_caching(self) -> bool:
        return False

    def setup_resources(self, context: ExecutionContext) -> None:
        if self.__es is None:
            context.logger.info(
                f'Initializing Elasticsearch client: {self.config.host}',
            )
            self.__es = ElasticsearchWrapper(
                host=self.config.host,
                index_name=self.config.index_name,
            )

    def teardown_resources(self, context: ExecutionContext) -> None:
        if self.__es:
            asyncio.run(self.__es.close())
            self.__es = None
            context.logger.info('Elasticsearch client closed')

    def cleanup(self) -> None:
        if self.__es:
            asyncio.run(self.__es.close())
            self.__es = None

    def execute_batch(
        self,
        input_data: List[List[ElasticDocuments]],
        context: ExecutionContext,
    ) -> List[IndexingResult]:
        context.logger.info(
            f"Batch indexing {len(input_data)} document collections",
        )
        results = []
        for docs in input_data:
            # Reusing _process logic via direct async call wrapper if needed,
            # or calling execute which routes to _process
            result = self.execute(docs, context)
            results.append(result)
        return results

    def _process(
        self, input_data: List[ElasticDocuments], context: ExecutionContext,
    ) -> IndexingResult:
        return asyncio.run(self.__process_async(input_data, context))

    async def __process_async(
        self,
        input_data: List[ElasticDocuments],
        context: ExecutionContext,
    ) -> IndexingResult:
        if not input_data:
            return self.__construct_empty_result(context)

        docs_by_type = self.__group_documents_by_type(input_data)
        total_indexed = await self.__index_grouped_documents(
            docs_by_type, context,
        )

        return self.__construct_indexing_result(total_indexed)

    async def __index_grouped_documents(
        self,
        docs_by_type: Dict[str, List[Path]],
        context: ExecutionContext,
    ) -> int:
        total_indexed: int = 0
        for doc_type, paths in docs_by_type.items():
            try:
                indexed_count = await self.__process_document_type(
                    doc_type, paths, context,
                )
                total_indexed += indexed_count
            except Exception as e:
                context.logger.error(
                    f'Elasticsearch indexing failed for {doc_type}: {e}',
                )
                raise
        return total_indexed

    async def __process_document_type(
        self,
        doc_type: str,
        paths: List[Path],
        context: ExecutionContext,
    ) -> int:
        index_name: str = f'{self.config.index_name}_{doc_type}'
        context.logger.info(f'Indexing {len(paths)} files into {index_name}')

        await self.__prepare_elasticsearch_client(index_name)
        await self.__setup_index(doc_type)

        documents = self.__load_documents_from_paths(paths)
        return await self.__execute_bulk_indexing(
            documents, index_name, context,
        )

    async def __prepare_elasticsearch_client(self, index_name: str) -> None:
        if self.__es is None or self.__es.index_name != index_name:
            if self.__es is not None:
                await self.__es.close()
            self.__es = ElasticsearchWrapper(
                index_name=index_name,
                host=self.config.host,
                dry_run=self.config.dry_run,
            )

    async def __setup_index(self, doc_type: str) -> None:
        if not self.config.append:
            await self.__es.delete_index()

        mapping: Optional[Dict[str, Any]] = self.__get_mapping_for_type(
            doc_type,
        )
        if mapping:
            await self.__es.create_index(mapping)

    async def __execute_bulk_indexing(
        self,
        documents: List[Dict[str, Any]],
        index_name: str,
        context: ExecutionContext,
    ) -> int:
        if not documents:
            return 0

        if not self.config.dry_run:
            await self.__es.bulk_index(documents)
            return len(documents)

        context.logger.info(
            f'Dry-run: would index {len(documents)} docs to {index_name}',
        )
        return 0

    def __construct_indexing_result(self, document_count: int) -> IndexingResult:
        return IndexingResult(
            index_name=self.config.index_name,
            document_count=document_count,
            success=True,
        )

    def __construct_empty_result(
        self, context: ExecutionContext,
    ) -> IndexingResult:
        context.logger.warning('No documents to index.')
        return self.__construct_indexing_result(0)

    @staticmethod
    def __group_documents_by_type(
        input_data: List[ElasticDocuments],
    ) -> Dict[str, List[Path]]:
        docs_by_type: Dict[str, List[Path]] = {}
        for doc_artifact in input_data:
            doc_type: str = doc_artifact.path.parent.name
            if doc_type not in docs_by_type:
                docs_by_type[doc_type] = []
            docs_by_type[doc_type].append(doc_artifact.path)
        return docs_by_type

    @staticmethod
    def __load_documents_from_paths(paths: List[Path]) -> List[Dict[str, Any]]:
        documents: List[Dict[str, Any]] = []
        for path in paths:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        documents.append(json.loads(line))
        return documents

    @staticmethod
    def __get_mapping_for_type(
        _doc_type: str,
    ) -> Optional[Dict[str, Any]]:
        return None

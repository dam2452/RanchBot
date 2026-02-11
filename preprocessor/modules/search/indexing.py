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
from preprocessor.lib.search.elasticsearch import ElasticsearchWrapper


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
            context.logger.warning('No documents to index.')
            return IndexingResult(
                index_name=self.config.index_name,
                document_count=0,
                success=True,
            )

        docs_by_type: Dict[str, List[Path]] = {}
        for doc_artifact in input_data:
            doc_type: str = doc_artifact.path.parent.name
            if doc_type not in docs_by_type:
                docs_by_type[doc_type] = []
            docs_by_type[doc_type].append(doc_artifact.path)

        total_indexed: int = 0
        for doc_type, paths in docs_by_type.items():
            index_name: str = f'{self.config.index_name}_{doc_type}'
            context.logger.info(f'Indexing {len(paths)} files into {index_name}')

            if self._es is None or self._es.index_name != index_name:
                if self._es is not None:
                    await self._es.close()
                self._es = ElasticsearchWrapper(
                    index_name=index_name,
                    host=self.config.host,
                    dry_run=self.config.dry_run,
                )

            try:
                if not self.config.append:
                    await self._es.delete_index()

                mapping: Optional[Dict[str, Any]] = self.__get_mapping_for_type(doc_type)
                if mapping:
                    await self._es.create_index(mapping)

                documents: List[Dict[str, Any]] = []
                for path in paths:
                    with open(path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                documents.append(json.loads(line))

                if documents:
                    if not self.config.dry_run:
                        await self._es.bulk_index(documents)
                        total_indexed += len(documents)
                    else:
                        context.logger.info(
                            f'Dry-run: would index {len(documents)} docs to {index_name}',
                        )
            except Exception as e:
                context.logger.error(f'Elasticsearch indexing failed for {index_name}: {e}')
                return IndexingResult(
                    index_name=self.config.index_name,
                    document_count=total_indexed,
                    success=False,
                )

        return IndexingResult(
            index_name=self.config.index_name,
            document_count=total_indexed,
            success=True,
        )

    @staticmethod
    def __get_mapping_for_type(
        doc_type: str,  # pylint: disable=unused-argument
    ) -> Optional[Dict[str, Any]]:
        return None

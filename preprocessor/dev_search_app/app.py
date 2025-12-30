# pylint: disable=duplicate-code
from pathlib import Path
from typing import Optional

from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="Ranczo Search Dev Tool")

es_client = None


class TextSearchRequest(BaseModel):
    query: str
    season: Optional[int] = None
    episode: Optional[int] = None
    limit: int = 20


class SemanticSearchRequest(BaseModel):
    query: str
    embedding: list[float]
    season: Optional[int] = None
    episode: Optional[int] = None
    limit: int = 10


@app.on_event("startup")
async def startup():
    global es_client
    es_client = AsyncElasticsearch(
        hosts=["http://localhost:9200"],
        verify_certs=False,
    )
    await es_client.ping()


@app.on_event("shutdown")
async def shutdown():
    if es_client:
        await es_client.close()


@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = Path(__file__).parent / "index.html"
    return html_path.read_text()


@app.get("/stats")
async def get_stats():
    segments_count = await es_client.count(index="ranczo_segments")
    text_emb_count = await es_client.count(index="ranczo_text_embeddings")
    video_emb_count = await es_client.count(index="ranczo_video_embeddings")

    return {
        "segments": segments_count["count"],
        "text_embeddings": text_emb_count["count"],
        "video_embeddings": video_emb_count["count"],
    }


@app.post("/search/text")
async def search_text(req: TextSearchRequest):
    must_clauses = [
        {
            "multi_match": {
                "query": req.query,
                "fields": ["text^2", "episode_metadata.title"],
                "fuzziness": "AUTO",
            },
        },
    ]

    if req.season is not None:
        must_clauses.append({"term": {"episode_metadata.season": req.season}})
    if req.episode is not None:
        must_clauses.append({"term": {"episode_metadata.episode_number": req.episode}})

    query = {
        "bool": {
            "must": must_clauses,
        },
    }

    result = await es_client.search(
        index="ranczo_segments",
        query=query,
        size=req.limit,
        _source=[
            "episode_id",
            "segment_id",
            "text",
            "start_time",
            "end_time",
            "speaker",
            "video_path",
            "episode_metadata",
        ],
    )

    hits = []
    for hit in result["hits"]["hits"]:
        hits.append({
            "score": hit["_score"],
            "episode_id": hit["_source"]["episode_id"],
            "segment_id": hit["_source"]["segment_id"],
            "text": hit["_source"]["text"],
            "start_time": hit["_source"]["start_time"],
            "end_time": hit["_source"]["end_time"],
            "speaker": hit["_source"]["speaker"],
            "video_path": hit["_source"]["video_path"],
            "episode_metadata": hit["_source"]["episode_metadata"],
        })

    return {
        "total": result["hits"]["total"]["value"],
        "hits": hits,
    }


@app.post("/search/semantic_text")
async def search_semantic_text(req: SemanticSearchRequest):
    filter_clauses = []

    if req.season is not None:
        filter_clauses.append({"term": {"episode_metadata.season": req.season}})
    if req.episode is not None:
        filter_clauses.append({"term": {"episode_metadata.episode_number": req.episode}})

    query = {
        "script_score": {
            "query": {
                "bool": {
                    "filter": filter_clauses,
                },
            } if filter_clauses else {"match_all": {}},
            "script": {
                "source": "cosineSimilarity(params.query_vector, 'text_embedding') + 1.0",
                "params": {"query_vector": req.embedding},
            },
        },
    }

    result = await es_client.search(
        index="ranczo_text_embeddings",
        query=query,
        size=req.limit,
        _source=["episode_id", "embedding_id", "text", "segment_range", "video_path", "episode_metadata"],
    )

    hits = []
    for hit in result["hits"]["hits"]:
        hits.append({
            "score": hit["_score"],
            "episode_id": hit["_source"]["episode_id"],
            "embedding_id": hit["_source"]["embedding_id"],
            "text": hit["_source"]["text"],
            "segment_range": hit["_source"]["segment_range"],
            "video_path": hit["_source"]["video_path"],
            "episode_metadata": hit["_source"]["episode_metadata"],
        })

    return {
        "total": result["hits"]["total"]["value"],
        "hits": hits,
    }


@app.post("/search/semantic_video")
async def search_semantic_video(req: SemanticSearchRequest):
    filter_clauses = []

    if req.season is not None:
        filter_clauses.append({"term": {"episode_metadata.season": req.season}})
    if req.episode is not None:
        filter_clauses.append({"term": {"episode_metadata.episode_number": req.episode}})

    query = {
        "script_score": {
            "query": {
                "bool": {
                    "filter": filter_clauses,
                },
            } if filter_clauses else {"match_all": {}},
            "script": {
                "source": "cosineSimilarity(params.query_vector, 'video_embedding') + 1.0",
                "params": {"query_vector": req.embedding},
            },
        },
    }

    result = await es_client.search(
        index="ranczo_video_embeddings",
        query=query,
        size=req.limit,
        _source=[
            "episode_id",
            "frame_number",
            "timestamp",
            "frame_type",
            "scene_number",
            "perceptual_hash",
            "video_path",
            "episode_metadata",
            "character_appearances",
        ],
    )

    hits = []
    for hit in result["hits"]["hits"]:
        hits.append({
            "score": hit["_score"],
            "episode_id": hit["_source"]["episode_id"],
            "frame_number": hit["_source"]["frame_number"],
            "timestamp": hit["_source"]["timestamp"],
            "frame_type": hit["_source"]["frame_type"],
            "scene_number": hit["_source"]["scene_number"],
            "perceptual_hash": hit["_source"]["perceptual_hash"],
            "video_path": hit["_source"]["video_path"],
            "episode_metadata": hit["_source"]["episode_metadata"],
            "character_appearances": hit["_source"].get("character_appearances", []),
        })

    return {
        "total": result["hits"]["total"]["value"],
        "hits": hits,
    }


@app.get("/search/perceptual_hash/{phash}")
async def search_by_perceptual_hash(phash: str, limit: int = 10):
    query = {
        "term": {
            "perceptual_hash": phash,
        },
    }

    result = await es_client.search(
        index="ranczo_video_embeddings",
        query=query,
        size=limit,
        _source=["episode_id", "frame_number", "timestamp", "video_path", "episode_metadata"],
    )

    hits = []
    for hit in result["hits"]["hits"]:
        hits.append({
            "score": hit["_score"],
            "episode_id": hit["_source"]["episode_id"],
            "frame_number": hit["_source"]["frame_number"],
            "timestamp": hit["_source"]["timestamp"],
            "video_path": hit["_source"]["video_path"],
            "episode_metadata": hit["_source"]["episode_metadata"],
        })

    return {
        "total": result["hits"]["total"]["value"],
        "hits": hits,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

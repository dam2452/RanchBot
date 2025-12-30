# pylint: disable=duplicate-code,too-many-arguments,too-many-statements
import asyncio
import json
from pathlib import Path
import sys

from PIL import Image
import click
from elasticsearch import AsyncElasticsearch
from qwen_vl_utils import process_vision_info
import torch
from transformers import (
    AutoProcessor,
    Qwen2VLForConditionalGeneration,
)

from preprocessor.embeddings.image_hasher import PerceptualHasher

_model = None
_processor = None
_device = None
_hasher = None


def load_model():
    global _model, _processor, _device  # pylint: disable=global-statement
    if _model is not None:
        return _model, _processor, _device

    click.echo("Loading embedding model...", err=True)
    model_name = "Alibaba-NLP/gme-Qwen2-VL-2B-Instruct"
    _device = "cuda" if torch.cuda.is_available() else "cpu"

    _model = Qwen2VLForConditionalGeneration.from_pretrained(
        model_name,
        torch_dtype=torch.bfloat16 if _device == "cuda" else torch.float32,
        device_map="auto" if _device == "cuda" else None,
    )
    _processor = AutoProcessor.from_pretrained(model_name)

    if _device == "cpu":
        _model = _model.to(_device)

    click.echo(f"Model loaded on {_device}", err=True)
    return _model, _processor, _device


def get_text_embedding(text):
    model, processor, device = load_model()

    messages = [{
        "role": "user",
        "content": [{"type": "text", "text": text}],
    }]

    text_inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_tensors="pt",
    ).to(device)

    with torch.no_grad():
        output = model(input_ids=text_inputs, output_hidden_states=True)
        embedding = output.hidden_states[-1][:, -1, :].squeeze(0)
        embedding = torch.nn.functional.normalize(embedding, p=2, dim=0)

    return embedding.cpu().numpy().tolist()


def get_image_embedding(image_path):
    model, processor, device = load_model()

    messages = [{
        "role": "user",
        "content": [
            {"type": "image", "image": image_path},
            {"type": "text", "text": "Describe this image."},
        ],
    }]

    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)

    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )
    inputs = inputs.to(device)

    with torch.no_grad():
        output = model(**inputs, output_hidden_states=True)
        embedding = output.hidden_states[-1][:, -1, :].squeeze(0)
        embedding = torch.nn.functional.normalize(embedding, p=2, dim=0)

    return embedding.cpu().numpy().tolist()


def load_hasher():
    global _hasher  # pylint: disable=global-statement
    if _hasher is not None:
        return _hasher

    click.echo("Loading perceptual hasher...", err=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    _hasher = PerceptualHasher(device=device, hash_size=8)
    click.echo(f"Hasher loaded on {device}", err=True)
    return _hasher


def get_perceptual_hash(image_path):
    hasher = load_hasher()
    image = Image.open(image_path).convert("RGB")
    hashes = hasher.compute_phash_batch([image])
    return hashes[0] if hashes else None


async def search_text_query(es_client, query, season=None, episode=None, limit=20):
    must_clauses = [{
        "multi_match": {
            "query": query,
            "fields": ["text^2", "episode_metadata.title"],
            "fuzziness": "AUTO",
        },
    }]

    if season is not None:
        must_clauses.append({"term": {"episode_metadata.season": season}})
    if episode is not None:
        must_clauses.append({"term": {"episode_metadata.episode_number": episode}})

    query_body = {"bool": {"must": must_clauses}}

    return await es_client.search(
        index="ranczo_segments",
        query=query_body,
        size=limit,
        _source=["episode_id", "segment_id", "text", "start_time", "end_time", "speaker", "video_path", "episode_metadata", "scene_info"],
    )


async def search_text_semantic(es_client, text, season=None, episode=None, limit=10):
    embedding = get_text_embedding(text)

    filter_clauses = []
    if season is not None:
        filter_clauses.append({"term": {"episode_metadata.season": season}})
    if episode is not None:
        filter_clauses.append({"term": {"episode_metadata.episode_number": episode}})

    query = {
        "script_score": {
            "query": {"bool": {"filter": filter_clauses}} if filter_clauses else {"match_all": {}},
            "script": {
                "source": "cosineSimilarity(params.query_vector, 'text_embedding') + 1.0",
                "params": {"query_vector": embedding},
            },
        },
    }

    return await es_client.search(
        index="ranczo_text_embeddings",
        query=query,
        size=limit,
        _source=[
            "episode_id", "embedding_id", "text", "segment_range",
            "video_path", "episode_metadata", "scene_info",
        ],
    )


async def search_video_semantic(es_client, image_path, season=None, episode=None, character=None, limit=10):
    embedding = get_image_embedding(image_path)

    filter_clauses = []
    if season is not None:
        filter_clauses.append({"term": {"episode_metadata.season": season}})
    if episode is not None:
        filter_clauses.append({"term": {"episode_metadata.episode_number": episode}})
    if character:
        filter_clauses.append({"term": {"character_appearances": character}})

    query = {
        "script_score": {
            "query": {"bool": {"filter": filter_clauses}} if filter_clauses else {"match_all": {}},
            "script": {
                "source": "cosineSimilarity(params.query_vector, 'video_embedding') + 1.0",
                "params": {"query_vector": embedding},
            },
        },
    }

    return await es_client.search(
        index="ranczo_video_embeddings",
        query=query,
        size=limit,
        _source=[
            "episode_id", "frame_number", "timestamp", "frame_type", "scene_number",
            "perceptual_hash", "video_path", "episode_metadata", "character_appearances", "scene_info",
        ],
    )


async def search_by_character(es_client, character, season=None, episode=None, limit=20):
    filter_clauses = [{"term": {"character_appearances": character}}]

    if season is not None:
        filter_clauses.append({"term": {"episode_metadata.season": season}})
    if episode is not None:
        filter_clauses.append({"term": {"episode_metadata.episode_number": episode}})

    return await es_client.search(
        index="ranczo_video_embeddings",
        query={"bool": {"filter": filter_clauses}},
        size=limit,
        _source=["episode_id", "frame_number", "timestamp", "video_path", "episode_metadata", "character_appearances", "scene_info"],
    )


async def search_perceptual_hash(es_client, phash, limit=10):
    return await es_client.search(
        index="ranczo_video_embeddings",
        query={"term": {"perceptual_hash": phash}},
        size=limit,
        _source=["episode_id", "frame_number", "timestamp", "video_path", "episode_metadata", "perceptual_hash", "scene_info"],
    )


async def list_characters(es_client):
    result = await es_client.search(
        index="ranczo_video_embeddings",
        size=0,
        aggs={"characters": {"terms": {"field": "character_appearances", "size": 1000}}},
    )
    buckets = result["aggregations"]["characters"]["buckets"]
    return [(b["key"], b["doc_count"]) for b in buckets]


async def get_stats(es_client):
    return {
        "segments": (await es_client.count(index="ranczo_segments"))["count"],
        "text_embeddings": (await es_client.count(index="ranczo_text_embeddings"))["count"],
        "video_embeddings": (await es_client.count(index="ranczo_video_embeddings"))["count"],
    }


def format_scene_context(scene_info):
    if not scene_info:
        return ""
    return f" [Scene {scene_info.get('scene_number', '?')}: {scene_info.get('scene_start_time', 0):.1f}s - {scene_info.get('scene_end_time', 0):.1f}s]"


def print_results(result, result_type="text"):
    total = result["hits"]["total"]["value"]
    hits = result["hits"]["hits"]

    click.echo(f"\nZnaleziono: {total} wynikow")
    click.echo("=" * 80)

    for i, hit in enumerate(hits, 1):
        source = hit["_source"]
        score = hit["_score"]
        meta = source["episode_metadata"]
        scene_ctx = format_scene_context(source.get("scene_info"))

        click.echo(f"\n[{i}] Score: {score:.2f}")
        click.echo(f"Episode: S{meta['season']:02d}E{meta['episode_number']:02d} - {meta.get('title', 'N/A')}")

        if result_type == "text":
            click.echo(f"Segment ID: {source.get('segment_id', 'N/A')}")
            click.echo(f"Time: {source['start_time']:.2f}s - {source['end_time']:.2f}s{scene_ctx}")
            click.echo(f"Speaker: {source.get('speaker', 'N/A')}")
            click.echo(f"Text: {source['text']}")
        elif result_type == "text_semantic":
            click.echo(f"Segments: {source['segment_range'][0]}-{source['segment_range'][1]}{scene_ctx}")
            click.echo(f"Embedding ID: {source.get('embedding_id', 'N/A')}")
            click.echo(f"Text: {source['text']}")
        else:
            click.echo(f"Frame: {source['frame_number']} @ {source['timestamp']:.2f}s{scene_ctx}")
            if "frame_type" in source:
                click.echo(f"Type: {source['frame_type']}")
            if "scene_number" in source:
                click.echo(f"Scene number: {source['scene_number']}")
            if "perceptual_hash" in source:
                click.echo(f"Hash: {source['perceptual_hash']}")
            if source.get("character_appearances"):
                click.echo(f"Characters: {', '.join(source['character_appearances'])}")

        click.echo(f"Path: {source['video_path']}")


@click.command(context_settings={"show_default": True})
@click.option("--text", type=str, help="Full-text search po transkrypcjach")
@click.option("--text-semantic", type=str, help="Semantic search po text embeddings")
@click.option("--image", type=click.Path(exists=True, path_type=Path), help="Semantic search po video embeddings")
@click.option("--hash", "phash", type=str, help="Szukaj po perceptual hash (podaj hash string lub sciezke do obrazka)")
@click.option("--character", type=str, help="Szukaj po postaci")
@click.option("--list-characters", "list_chars_flag", is_flag=True, help="Lista wszystkich postaci")
@click.option("--season", type=int, help="Filtruj po sezonie")
@click.option("--episode", type=int, help="Filtruj po odcinku")
@click.option("--limit", type=int, default=20, help="Limit wynikow")
@click.option("--stats", is_flag=True, help="Pokaz statystyki indeksow")
@click.option("--json-output", is_flag=True, help="Output w formacie JSON")
@click.option("--host", type=str, default="http://localhost:9200", help="Elasticsearch host")
def search(text, text_semantic, image, phash, character, list_chars_flag, season, episode, limit, stats, json_output, host):
    """Search tool - comprehensive Elasticsearch search"""

    if not any([text, text_semantic, image, phash, character, list_chars_flag, stats]):
        click.echo("Podaj przynajmniej jedna opcje wyszukiwania. Uzyj --help", err=True)
        sys.exit(1)

    hash_value = None
    if phash:
        phash_path = Path(phash)
        if phash_path.exists() and phash_path.is_file():
            click.echo(f"Computing perceptual hash from image: {phash}", err=True)
            hash_value = get_perceptual_hash(str(phash_path))
            if hash_value:
                click.echo(f"Computed hash: {hash_value}", err=True)
            else:
                click.echo("Failed to compute hash from image", err=True)
                sys.exit(1)
        else:
            hash_value = phash

    async def run():  # pylint: disable=too-many-branches,too-many-nested-blocks
        es_client = AsyncElasticsearch(hosts=[host], verify_certs=False)

        try:
            await es_client.ping()
        except ConnectionError as e:
            click.echo(f"Blad polaczenia z Elasticsearch: {e}", err=True)
            sys.exit(1)

        try:
            if stats:
                result = await get_stats(es_client)
                if json_output:
                    click.echo(json.dumps(result, indent=2))
                else:
                    click.echo("\nStatystyki:")
                    click.echo(f"  Segments: {result['segments']:,}")
                    click.echo(f"  Text Embeddings: {result['text_embeddings']:,}")
                    click.echo(f"  Video Embeddings: {result['video_embeddings']:,}")

            elif list_chars_flag:
                chars = await list_characters(es_client)
                if json_output:
                    click.echo(json.dumps(chars, indent=2))
                else:
                    click.echo(f"\nZnaleziono {len(chars)} postaci:")
                    for char, count in sorted(chars, key=lambda x: -x[1]):
                        click.echo(f"  {char}: {count:,} wystapien")

            elif text:
                result = await search_text_query(es_client, text, season, episode, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    print_results(result, "text")

            elif text_semantic:
                result = await search_text_semantic(es_client, text_semantic, season, episode, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    print_results(result, "text_semantic")

            elif image:
                result = await search_video_semantic(es_client, str(image), season, episode, character, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    print_results(result, "video")

            elif character:
                result = await search_by_character(es_client, character, season, episode, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    print_results(result, "video")

            elif hash_value:
                result = await search_perceptual_hash(es_client, hash_value, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    print_results(result, "video")

        finally:
            await es_client.close()

    asyncio.run(run())

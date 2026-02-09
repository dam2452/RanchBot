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
    AutoModelForVision2Seq,
    AutoProcessor,
)

from preprocessor.config.config import settings
from preprocessor.utils.image_hasher import PerceptualHasher
from preprocessor.utils.constants import (
    ElasticsearchAggregationKeys,
    ElasticsearchKeys,
    EpisodeMetadataKeys,
)

_model = None
_processor = None
_device = None
_hasher = None


def load_model():
    global _model, _processor, _device  # pylint: disable=global-statement
    if _model is not None:
        return _model, _processor, _device

    click.echo("Loading embedding model...", err=True)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required but not available. This pipeline requires GPU.")

    model_name = settings.embedding_model.model_name
    _device = "cuda"

    _model = AutoModelForVision2Seq.from_pretrained(
        model_name,
        dtype=torch.bfloat16,
        device_map="auto",
    )
    _processor = AutoProcessor.from_pretrained(model_name)

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

    return embedding.float().cpu().numpy().tolist()


def _get_image_embedding(image_path):
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

    return embedding.float().cpu().numpy().tolist()


def _load_hasher():
    global _hasher  # pylint: disable=global-statement
    if _hasher is not None:
        return _hasher

    click.echo("Loading perceptual hasher...", err=True)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required but not available. This pipeline requires GPU.")

    _hasher = PerceptualHasher(device="cuda", hash_size=8)
    click.echo("Hasher loaded on cuda", err=True)
    return _hasher


def _get_perceptual_hash(image_path):
    hasher = _load_hasher()
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

    knn_query = {
        "field": "text_embedding",
        "query_vector": embedding,
        "k": limit,
        "num_candidates": limit * 10,
    }
    if filter_clauses:
        knn_query["filter"] = filter_clauses

    return await es_client.search(
        index="ranczo_text_embeddings",
        knn=knn_query,
        size=limit,
        _source=[
            "episode_id", "embedding_id", "text", "segment_range",
            "video_path", "episode_metadata", "scene_info",
        ],
    )


async def search_video_semantic(es_client, image_path, season=None, episode=None, character=None, limit=10):
    embedding = _get_image_embedding(image_path)

    filter_clauses = []
    if season is not None:
        filter_clauses.append({"term": {"episode_metadata.season": season}})
    if episode is not None:
        filter_clauses.append({"term": {"episode_metadata.episode_number": episode}})
    if character:
        filter_clauses.append({
            "nested": {
                "path": "character_appearances",
                "query": {"term": {"character_appearances.name": character}},
            },
        })

    knn_query = {
        "field": "video_embedding",
        "query_vector": embedding,
        "k": limit,
        "num_candidates": limit * 10,
    }
    if filter_clauses:
        knn_query["filter"] = filter_clauses

    return await es_client.search(
        index="ranczo_video_frames",
        knn=knn_query,
        size=limit,
        _source=[
            "episode_id", "frame_number", "timestamp", "frame_type", "scene_number",
            "perceptual_hash", "video_path", "episode_metadata", "character_appearances", "scene_info",
        ],
    )


async def search_text_to_video(es_client, text, season=None, episode=None, character=None, limit=10):
    embedding = get_text_embedding(text)

    filter_clauses = []
    if season is not None:
        filter_clauses.append({"term": {"episode_metadata.season": season}})
    if episode is not None:
        filter_clauses.append({"term": {"episode_metadata.episode_number": episode}})
    if character:
        filter_clauses.append({
            "nested": {
                "path": "character_appearances",
                "query": {"term": {"character_appearances.name": character}},
            },
        })

    knn_query = {
        "field": "video_embedding",
        "query_vector": embedding,
        "k": limit,
        "num_candidates": limit * 10,
    }
    if filter_clauses:
        knn_query["filter"] = filter_clauses

    return await es_client.search(
        index="ranczo_video_frames",
        knn=knn_query,
        size=limit,
        _source=[
            "episode_id", "frame_number", "timestamp", "frame_type", "scene_number",
            "perceptual_hash", "video_path", "episode_metadata", "character_appearances", "scene_info",
        ],
    )


async def search_by_character(es_client, character, season=None, episode=None, limit=20):
    must_clauses = [{
        "nested": {
            "path": "character_appearances",
            "query": {"term": {"character_appearances.name": character}},
        },
    }]

    if season is not None:
        must_clauses.append({"term": {"episode_metadata.season": season}})
    if episode is not None:
        must_clauses.append({"term": {"episode_metadata.episode_number": episode}})

    return await es_client.search(
        index="ranczo_video_frames",
        query={"bool": {"must": must_clauses}},
        size=limit,
        _source=["episode_id", "frame_number", "timestamp", "video_path", "episode_metadata", "character_appearances", "scene_info"],
    )


async def search_by_emotion(es_client, emotion, season=None, episode=None, character=None, limit=20):
    nested_must = [{"term": {"character_appearances.emotion.label": emotion}}]
    if character:
        nested_must.append({"term": {"character_appearances.name": character}})

    must_clauses = [{
        "nested": {
            "path": "character_appearances",
            "query": {"bool": {"must": nested_must}},
        },
    }]

    if season is not None:
        must_clauses.append({"term": {"episode_metadata.season": season}})
    if episode is not None:
        must_clauses.append({"term": {"episode_metadata.episode_number": episode}})

    nested_filter = {"term": {"character_appearances.emotion.label": emotion}}
    if character:
        nested_filter = {
            "bool": {
                "must": [
                    {"term": {"character_appearances.emotion.label": emotion}},
                    {"term": {"character_appearances.name": character}},
                ],
            },
        }

    return await es_client.search(
        index="ranczo_video_frames",
        query={"bool": {"must": must_clauses}},
        sort=[
            {
                "character_appearances.emotion.confidence": {
                    "order": "desc",
                    "nested": {
                        "path": "character_appearances",
                        "filter": nested_filter,
                    },
                },
            },
        ],
        track_scores=True,
        size=limit,
        _source=["episode_id", "frame_number", "timestamp", "video_path", "episode_metadata", "character_appearances", "scene_info"],
    )


async def search_by_object(es_client, object_query, season=None, episode=None, limit=20):
    filter_clauses = []
    if season is not None:
        filter_clauses.append({"term": {"episode_metadata.season": season}})
    if episode is not None:
        filter_clauses.append({"term": {"episode_metadata.episode_number": episode}})

    must_clauses = []

    if ":" in object_query:
        object_class, count_filter = object_query.split(":", 1)
        object_class = object_class.strip()

        if count_filter.endswith("+"):
            min_count = int(count_filter[:-1])
            must_clauses.append({
                "nested": {
                    "path": "detected_objects",
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"detected_objects.class": object_class}},
                                {"range": {"detected_objects.count": {"gte": min_count}}},
                            ],
                        },
                    },
                },
            })
        elif "-" in count_filter:
            min_c, max_c = count_filter.split("-")
            must_clauses.append({
                "nested": {
                    "path": "detected_objects",
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"detected_objects.class": object_class}},
                                {"range": {"detected_objects.count": {"gte": int(min_c), "lte": int(max_c)}}},
                            ],
                        },
                    },
                },
            })
        else:
            exact_count = int(count_filter)
            must_clauses.append({
                "nested": {
                    "path": "detected_objects",
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"detected_objects.class": object_class}},
                                {"term": {"detected_objects.count": exact_count}},
                            ],
                        },
                    },
                },
            })
    else:
        must_clauses.append({
            "nested": {
                "path": "detected_objects",
                "query": {
                    "term": {"detected_objects.class": object_query.strip()},
                },
            },
        })

    query_body = {
        "bool": {
            "must": must_clauses,
            "filter": filter_clauses,
        },
    }

    object_class = object_query.split(":")[0].strip() if ":" in object_query else object_query.strip()

    return await es_client.search(
        index="ranczo_video_frames",
        query=query_body,
        sort=[
            {
                "detected_objects.count": {
                    "order": "desc",
                    "nested": {
                        "path": "detected_objects",
                        "filter": {"term": {"detected_objects.class": object_class}},
                    },
                },
            },
        ],
        track_scores=True,
        size=limit,
        _source=["episode_id", "frame_number", "timestamp", "detected_objects", "character_appearances", "video_path", "episode_metadata", "scene_info"],
    )


async def search_perceptual_hash(es_client, phash, limit=10):
    return await es_client.search(
        index="ranczo_video_frames",
        query={"term": {"perceptual_hash": phash}},
        size=limit,
        _source=["episode_id", "frame_number", "timestamp", "video_path", "episode_metadata", "perceptual_hash", "scene_info"],
    )


async def list_characters(es_client):
    result = await es_client.search(
        index="ranczo_video_frames",
        size=0,
        aggs={
            "characters_nested": {
                "nested": {"path": "character_appearances"},
                "aggs": {
                    "character_names": {
                        "terms": {"field": "character_appearances.name", "size": 1000},
                    },
                },
            },
        },
    )
    buckets = result["aggregations"]["characters_nested"]["character_names"]["buckets"]
    return [(b["key"], b["doc_count"]) for b in buckets]


async def list_objects(es_client):
    result = await es_client.search(
        index="ranczo_video_frames",
        size=0,
        aggs={
            "objects_nested": {
                "nested": {"path": "detected_objects"},
                "aggs": {
                    "object_classes": {
                        "terms": {"field": "detected_objects.class", "size": 1000},
                    },
                },
            },
        },
    )
    buckets = result["aggregations"]["objects_nested"]["object_classes"]["buckets"]
    return [(b["key"], b["doc_count"]) for b in buckets]


async def search_episode_name(es_client, query, season=None, limit=20):
    must_clauses = [{
        "multi_match": {
            "query": query,
            "fields": ["title^2", "episode_metadata.title"],
            "fuzziness": "AUTO",
        },
    }]

    if season is not None:
        must_clauses.append({"term": {"episode_metadata.season": season}})

    query_body = {"bool": {"must": must_clauses}}

    return await es_client.search(
        index="ranczo_episode_names",
        query=query_body,
        size=limit,
        _source=["episode_id", "title", "video_path", "episode_metadata"],
    )


async def search_episode_name_semantic(es_client, text, season=None, limit=10):
    embedding = get_text_embedding(text)

    filter_clauses = []
    if season is not None:
        filter_clauses.append({"term": {"episode_metadata.season": season}})

    knn_query = {
        "field": "title_embedding",
        "query_vector": embedding,
        "k": limit,
        "num_candidates": limit * 10,
    }
    if filter_clauses:
        knn_query["filter"] = filter_clauses

    return await es_client.search(
        index="ranczo_episode_names",
        knn=knn_query,
        size=limit,
        _source=["episode_id", "title", "video_path", "episode_metadata"],
    )


async def get_stats(es_client):
    return {
        "segments": (await es_client.count(index="ranczo_segments"))["count"],
        "text_embeddings": (await es_client.count(index="ranczo_text_embeddings"))["count"],
        "video_embeddings": (await es_client.count(index="ranczo_video_frames"))["count"],
        "episode_names": (await es_client.count(index="ranczo_episode_names"))["count"],
    }


def format_timestamp(seconds):
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"


def _format_scene_context(scene_info):
    if not scene_info:
        return ""
    start = format_timestamp(scene_info.get('scene_start_time', 0))
    end = format_timestamp(scene_info.get('scene_end_time', 0))
    return f" [Scene {scene_info.get('scene_number', '?')}: {start} - {end}]"


def _print_results(result, result_type="text"):  # pylint: disable=too-many-locals
    total = result[ElasticsearchKeys.HITS][ElasticsearchKeys.TOTAL][ElasticsearchAggregationKeys.VALUE]
    hits = result[ElasticsearchKeys.HITS][ElasticsearchKeys.HITS]

    click.echo(f"\nZnaleziono: {total} wynikow")
    click.echo("=" * 80)

    for i, hit in enumerate(hits, 1):
        source = hit[ElasticsearchKeys.SOURCE]
        score = hit[ElasticsearchKeys.SCORE]
        meta = source[EpisodeMetadataKeys.EPISODE_METADATA]
        scene_ctx = _format_scene_context(source.get("scene_info"))

        click.echo(f"\n[{i}] Score: {score:.2f}")
        season_code = "S00" if meta['season'] == 0 else f"S{meta['season']:02d}"
        click.echo(f"Episode: {season_code}E{meta['episode_number']:02d} - {meta.get('title', 'N/A')}")

        if result_type == "text":
            click.echo(f"Segment ID: {source.get('segment_id', 'N/A')}")
            start_time = format_timestamp(source['start_time'])
            end_time = format_timestamp(source['end_time'])
            click.echo(f"Time: {start_time} - {end_time}{scene_ctx}")
            click.echo(f"Speaker: {source.get('speaker', 'N/A')}")
            click.echo(f"Text: {source['text']}")
        elif result_type == "text_semantic":
            click.echo(f"Segments: {source['segment_range'][0]}-{source['segment_range'][1]}{scene_ctx}")
            click.echo(f"Embedding ID: {source.get('embedding_id', 'N/A')}")
            click.echo(f"Text: {source['text']}")
        elif result_type == "episode_name":
            click.echo(f"Episode Title: {source.get('title', 'N/A')}")
        else:
            timestamp = format_timestamp(source['timestamp'])
            click.echo(f"Frame: {source['frame_number']} @ {timestamp}{scene_ctx}")
            if "frame_type" in source:
                click.echo(f"Type: {source['frame_type']}")
            if "scene_number" in source:
                click.echo(f"Scene number: {source['scene_number']}")
            if "perceptual_hash" in source:
                click.echo(f"Hash: {source['perceptual_hash']}")
            if source.get("character_appearances"):
                chars_strs = []
                for char in source['character_appearances']:
                    char_str = char.get('name', 'Unknown')
                    if char.get('emotion'):
                        emotion_label = char['emotion'].get('label', '?')
                        emotion_conf = char['emotion'].get('confidence', 0)
                        char_str += f" ({emotion_label} {emotion_conf:.2f})"
                    chars_strs.append(char_str)
                click.echo(f"Characters: {', '.join(chars_strs)}")
            if source.get("detected_objects"):
                objects_str = ", ".join([f"{obj['class']}:{obj['count']}" for obj in source['detected_objects']])
                click.echo(f"Objects: {objects_str}")

        click.echo(f"Path: {source['video_path']}")


@click.command(context_settings={"show_default": True})
@click.option("--text", type=str, help="Full-text search po transkrypcjach")
@click.option("--text-semantic", type=str, help="Semantic search po text embeddings")
@click.option("--text-to-video", type=str, help="Cross-modal search: text query w video embeddings")
@click.option("--image", type=click.Path(exists=True, path_type=Path), help="Semantic search po video embeddings")
@click.option("--hash", "phash", type=str, help="Szukaj po perceptual hash (podaj hash string lub sciezke do obrazka)")
@click.option("--character", type=str, help="Szukaj po postaci")
@click.option("--emotion", type=str, help="Szukaj po emocji (neutral, happiness, surprise, sadness, anger, disgust, fear, contempt)")
@click.option("--object", "object_query", type=str, help="Szukaj po wykrytych obiektach (np. 'dog', 'person:5+', 'chair:2-4')")
@click.option("--episode-name", type=str, help="Fuzzy search po nazwach odcinkow")
@click.option("--episode-name-semantic", type=str, help="Semantic search po nazwach odcinkow")
@click.option("--list-characters", "list_chars_flag", is_flag=True, help="Lista wszystkich postaci")
@click.option("--list-objects", "list_objects_flag", is_flag=True, help="Lista wszystkich klas obiektow")
@click.option("--season", type=int, help="Filtruj po sezonie")
@click.option("--episode", type=int, help="Filtruj po odcinku")
@click.option("--limit", type=int, default=20, help="Limit wynikow")
@click.option("--stats", is_flag=True, help="Pokaz statystyki indeksow")
@click.option("--json-output", is_flag=True, help="Output w formacie JSON")
@click.option("--host", type=str, default="http://localhost:9200", help="Elasticsearch host")
def search(  # pylint: disable=too-many-locals
    text, text_semantic, text_to_video, image, phash, character, emotion, object_query, episode_name,
    episode_name_semantic, list_chars_flag, list_objects_flag, season, episode, limit,
    stats, json_output, host,
):
    """Search tool - comprehensive Elasticsearch search"""

    if not any([
        text, text_semantic, text_to_video, image, phash, character, emotion,
        object_query, episode_name, episode_name_semantic, list_chars_flag, list_objects_flag, stats,
    ]):
        click.echo("Podaj przynajmniej jedna opcje wyszukiwania. Uzyj --help", err=True)
        sys.exit(1)

    hash_value = None
    if phash:
        phash_path = Path(phash)
        if phash_path.exists() and phash_path.is_file():
            click.echo(f"Computing perceptual hash from image: {phash}", err=True)
            hash_value = _get_perceptual_hash(str(phash_path))
            if hash_value:
                click.echo(f"Computed hash: {hash_value}", err=True)
            else:
                click.echo("Failed to compute hash from image", err=True)
                sys.exit(1)
        else:
            hash_value = phash

    async def run():  # pylint: disable=too-many-branches
        es_client = AsyncElasticsearch(hosts=[host], verify_certs=False)

        try:
            await es_client.ping()
        except Exception:
            click.echo(f"✗ Cannot connect to Elasticsearch at {host}", err=True)
            click.echo("Make sure Elasticsearch is running:", err=True)
            click.echo("  docker-compose -f docker-compose.test.yml up -d", err=True)
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
                    click.echo(f"  Episode Names: {result['episode_names']:,}")

            elif list_chars_flag:
                chars = await list_characters(es_client)
                if json_output:
                    click.echo(json.dumps(chars, indent=2))
                else:
                    click.echo(f"\nZnaleziono {len(chars)} postaci:")
                    for char, count in sorted(chars, key=lambda x: -x[1]):
                        click.echo(f"  {char}: {count:,} wystapien")

            elif list_objects_flag:
                objects = await list_objects(es_client)
                if json_output:
                    click.echo(json.dumps(objects, indent=2))
                else:
                    click.echo(f"\nZnaleziono {len(objects)} klas obiektow:")
                    for obj, count in sorted(objects, key=lambda x: -x[1]):
                        click.echo(f"  {obj}: {count:,} wystapien")

            elif text:
                result = await search_text_query(es_client, text, season, episode, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    _print_results(result, "text")

            elif text_semantic:
                result = await search_text_semantic(es_client, text_semantic, season, episode, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    _print_results(result, "text_semantic")

            elif text_to_video:
                result = await search_text_to_video(es_client, text_to_video, season, episode, character, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    _print_results(result, "video")

            elif image:
                result = await search_video_semantic(es_client, str(image), season, episode, character, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    _print_results(result, "video")

            elif emotion:
                result = await search_by_emotion(es_client, emotion, season, episode, character, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    _print_results(result, "video")

            elif character:
                result = await search_by_character(es_client, character, season, episode, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    _print_results(result, "video")

            elif object_query:
                result = await search_by_object(es_client, object_query, season, episode, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    _print_results(result, "video")

            elif hash_value:
                result = await search_perceptual_hash(es_client, hash_value, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    _print_results(result, "video")

            elif episode_name:
                result = await search_episode_name(es_client, episode_name, season, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    _print_results(result, "episode_name")

            elif episode_name_semantic:
                result = await search_episode_name_semantic(es_client, episode_name_semantic, season, limit)
                if json_output:
                    click.echo(json.dumps(result["hits"], indent=2))
                else:
                    _print_results(result, "episode_name")

        finally:
            await es_client.close()

    asyncio.run(run())

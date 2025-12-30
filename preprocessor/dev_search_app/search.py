#!/usr/bin/env python3
# pylint: disable=duplicate-code
import argparse
import asyncio
import json
import sys

from elasticsearch import AsyncElasticsearch


async def search_text(es_client, query, season=None, episode=None, limit=20):
    must_clauses = [
        {
            "multi_match": {
                "query": query,
                "fields": ["text^2", "episode_metadata.title"],
                "fuzziness": "AUTO",
            },
        },
    ]

    if season is not None:
        must_clauses.append({"term": {"episode_metadata.season": season}})
    if episode is not None:
        must_clauses.append({"term": {"episode_metadata.episode_number": episode}})

    query_body = {"bool": {"must": must_clauses}}

    result = await es_client.search(
        index="ranczo_segments",
        query=query_body,
        size=limit,
        _source=["episode_id", "segment_id", "text", "start_time", "end_time", "speaker", "video_path", "episode_metadata"],
    )

    return result


async def search_perceptual_hash(es_client, phash, limit=10):
    query = {"term": {"perceptual_hash": phash}}

    result = await es_client.search(
        index="ranczo_video_embeddings",
        query=query,
        size=limit,
        _source=["episode_id", "frame_number", "timestamp", "video_path", "episode_metadata", "perceptual_hash"],
    )

    return result


async def get_stats(es_client):
    segments_count = await es_client.count(index="ranczo_segments")
    text_emb_count = await es_client.count(index="ranczo_text_embeddings")
    video_emb_count = await es_client.count(index="ranczo_video_embeddings")

    return {
        "segments": segments_count["count"],
        "text_embeddings": text_emb_count["count"],
        "video_embeddings": video_emb_count["count"],
    }


def print_text_results(result):
    total = result["hits"]["total"]["value"]
    hits = result["hits"]["hits"]

    print(f"\nZnaleziono: {total} wynikow")
    print("=" * 80)

    for i, hit in enumerate(hits, 1):
        source = hit["_source"]
        score = hit["_score"]
        meta = source["episode_metadata"]

        print(f"\n[{i}] Score: {score:.2f}")
        print(f"Episode: S{meta['season']:02d}E{meta['episode_number']:02d} - {meta.get('title', 'N/A')}")
        print(f"Time: {source['start_time']:.2f}s - {source['end_time']:.2f}s")
        print(f"Speaker: {source.get('speaker', 'N/A')}")
        print(f"Text: {source['text']}")
        print(f"Path: {source['video_path']}")


def print_hash_results(result):
    total = result["hits"]["total"]["value"]
    hits = result["hits"]["hits"]

    print(f"\nZnaleziono: {total} wynikow")
    print("=" * 80)

    for i, hit in enumerate(hits, 1):
        source = hit["_source"]
        score = hit["_score"]
        meta = source["episode_metadata"]

        print(f"\n[{i}] Score: {score:.2f}")
        print(f"Episode: S{meta['season']:02d}E{meta['episode_number']:02d} - {meta.get('title', 'N/A')}")
        print(f"Frame: {source['frame_number']} @ {source['timestamp']:.2f}s")
        print(f"Hash: {source.get('perceptual_hash', 'N/A')}")
        print(f"Path: {source['video_path']}")


async def main():
    parser = argparse.ArgumentParser(
        description="Ranczo Search CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python search.py --text "Kto tu rzadzi" --limit 5
  python search.py --text "Solejukowa" --season 10
  python search.py --hash 191b075b6d0363cf
  python search.py --stats
        """,
    )

    parser.add_argument("--text", type=str, help="Szukaj po tekscie")
    parser.add_argument("--hash", type=str, help="Szukaj po perceptual hash")
    parser.add_argument("--season", type=int, help="Filtruj po sezonie")
    parser.add_argument("--episode", type=int, help="Filtruj po odcinku")
    parser.add_argument("--limit", type=int, default=20, help="Limit wynikow (default: 20)")
    parser.add_argument("--stats", action="store_true", help="Pokaz statystyki indeksow")
    parser.add_argument("--json", action="store_true", help="Output w formacie JSON")
    parser.add_argument("--host", type=str, default="http://localhost:9200", help="Elasticsearch host")

    args = parser.parse_args()

    if not any([args.text, args.hash, args.stats]):
        parser.print_help()
        sys.exit(1)

    es_client = AsyncElasticsearch(
        hosts=[args.host],
        verify_certs=False,
    )

    try:
        await es_client.ping()
    except ConnectionError as e:
        print(f"Blad polaczenia z Elasticsearch: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        if args.stats:
            stats = await get_stats(es_client)
            if args.json:
                print(json.dumps(stats, indent=2))
            else:
                print("\nStatystyki:")
                print(f"  Segments: {stats['segments']:,}")
                print(f"  Text Embeddings: {stats['text_embeddings']:,}")
                print(f"  Video Embeddings: {stats['video_embeddings']:,}")

        elif args.text:
            result = await search_text(es_client, args.text, args.season, args.episode, args.limit)
            if args.json:
                print(json.dumps(result["hits"], indent=2))
            else:
                print_text_results(result)

        elif args.hash:
            result = await search_perceptual_hash(es_client, args.hash, args.limit)
            if args.json:
                print(json.dumps(result["hits"], indent=2))
            else:
                print_hash_results(result)

    finally:
        await es_client.close()


if __name__ == "__main__":
    asyncio.run(main())

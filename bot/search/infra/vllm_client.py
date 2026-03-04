import logging
from typing import List

import aiohttp

from bot.exceptions.vllm_exceptions import (
    VllmConnectionError,
    VllmRequestError,
    VllmTimeoutError,
)
from bot.settings import settings


class VllmClient:
    @staticmethod
    async def get_text_embedding(text: str, logger: logging.Logger) -> List[float]:
        embeddings = await VllmClient.get_text_embeddings_batch([text], logger)
        return embeddings[0]

    @staticmethod
    async def get_text_embeddings_batch(
        texts: List[str],
        logger: logging.Logger,
    ) -> List[List[float]]:
        url = f"{settings.VLLM_HOST}/v1/embeddings"
        payload = {"input": texts, "model": settings.VLLM_EMBEDDINGS_MODEL}
        timeout = aiohttp.ClientTimeout(total=settings.VLLM_TIMEOUT_SECONDS)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.error("vLLM proxy returned %d: %s", resp.status, body)
                        raise VllmRequestError(f"vLLM proxy returned {resp.status}: {body}")
                    data = await resp.json()
        except aiohttp.ServerConnectionError as exc:
            logger.error("Cannot connect to vLLM proxy at %s: %s", url, exc)
            raise VllmConnectionError(f"Cannot connect to vLLM proxy at {url}") from exc
        except aiohttp.ClientConnectorError as exc:
            logger.error("Cannot connect to vLLM proxy at %s: %s", url, exc)
            raise VllmConnectionError(f"Cannot connect to vLLM proxy at {url}") from exc
        except aiohttp.ServerTimeoutError as exc:
            logger.error("vLLM proxy timed out after %ds", settings.VLLM_TIMEOUT_SECONDS)
            raise VllmTimeoutError("vLLM proxy request timed out") from exc

        items = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in items]

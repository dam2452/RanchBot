import json
from typing import (
    List,
    Optional,
)

from openai import OpenAI
from pydantic import BaseModel
from rich.console import Console

console = Console()


class EpisodeInfo(BaseModel):
    episode_number: int
    title: str
    premiere_date: str
    viewership: int


class SeasonMetadata(BaseModel):
    season_number: int
    episodes: List[EpisodeInfo]


class EpisodeMetadata(BaseModel):
    title: str
    description: str
    summary: str
    season: Optional[int] = None
    episode_number: Optional[int] = None


class LLMProvider:
    PROVIDERS = {
        "lmstudio": {
            "base_url": "http://192.168.1.209:1235/v1",
            "api_key": "lm-studio",
            "model": "qwen/qwen3-coder-30b",
        },
        "ollama": {
            "base_url": "http://localhost:11434/v1",
            "api_key": "ollama",
            "model": "gpt-oss:20b",
        },
        "gemini": {
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "api_key": None,
            "model": "gemini-2.5-flash",
        },
    }

    def __init__(self, provider: str = "lmstudio", api_key: Optional[str] = None, model: Optional[str] = None):
        if provider not in self.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}. Available: {list(self.PROVIDERS.keys())}")

        config = self.PROVIDERS[provider]
        self.provider = provider
        self.base_url = config["base_url"]
        self.api_key = api_key or config["api_key"]
        self.model = model or config["model"]

        if provider == "gemini" and not api_key:
            raise ValueError("Gemini provider requires API key. Set --api-key or GEMINI_API_KEY env var")

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )

        console.print(f"[cyan]LLM Provider: {provider} (model: {self.model})[/cyan]")

    def extract_season_episodes(self, page_text: str, url: str) -> Optional[SeasonMetadata]:
        system_prompt = """You are extracting episode data from a TV series page.
Extract ALL episodes you can find on the page. Look for tables, lists, or any structured data.

For each episode extract:
- episode_number: integer
- title: string (clean title without markdown formatting)
- premiere_date: string (date format as found on page)
- viewership: integer (remove spaces from numbers like "4 396 564" -> 4396564, use 0 if not available)

The season number should be determined from the page content or URL."""

        user_prompt = f"""URL: {url}

Page content (markdown):
{page_text[:15000]}

Extract ALL episodes from this page and return as JSON."""

        try:
            # noinspection PyTypeChecker
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "SeasonMetadata",
                        "strict": True,
                        "schema": SeasonMetadata.model_json_schema(),
                    },
                },
                max_tokens=4096,
                temperature=0.1,
            )

            content = response.choices[0].message.content
            data = json.loads(content)
            metadata = SeasonMetadata(**data)
            return metadata

        except Exception as e:  # pylint: disable=broad-exception-caught
            console.print(f"[red]LLM extraction failed for {url}: {e}[/red]")
            return None

    def extract_episode_metadata(self, page_text: str, url: str) -> Optional[EpisodeMetadata]:
        system_prompt = """Extract episode information from the provided web page content.
Focus on finding:
- Episode title (exact title, not description)
- Episode description (1-2 sentences summarizing the plot)
- Episode summary (detailed summary, 3-5 sentences)
- Season number (if mentioned)
- Episode number (if mentioned)

If information is missing, use empty string for text fields and null for numbers.
Be precise and extract only factual information from the text."""

        user_prompt = f"""URL: {url}

Page content:
{page_text[:8000]}

Extract the episode metadata from above."""

        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[  # type: ignore[arg-type]
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=EpisodeMetadata,
            )

            metadata = response.choices[0].message.parsed
            return metadata

        except Exception as e:  # pylint: disable=broad-exception-caught
            console.print(f"[red]LLM extraction failed for {url}: {e}[/red]")
            return None

    def merge_episode_data(self, metadata_list: List[EpisodeMetadata]) -> EpisodeMetadata:
        if not metadata_list:
            raise ValueError("No metadata to merge")

        if len(metadata_list) == 1:
            return metadata_list[0]

        combined_text = "\n\n---\n\n".join([
            f"Source {i+1}:\nTitle: {m.title}\nDescription: {m.description}\nSummary: {m.summary}\nSeason: {m.season}\nEpisode: {m.episode_number}"
            for i, m in enumerate(metadata_list)
        ])

        system_prompt = """You are merging episode information from multiple sources.
Create a single, accurate metadata entry by:
- Choosing the most complete and accurate title
- Combining descriptions into a coherent 1-2 sentence description
- Merging summaries into a comprehensive 3-5 sentence summary
- Using the most reliable season/episode numbers

Prefer longer, more detailed information when merging."""

        user_prompt = f"""Merge the following episode metadata from {len(metadata_list)} sources:

{combined_text}

Create a single, unified metadata entry."""

        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[  # type: ignore[arg-type]
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=EpisodeMetadata,
            )

            merged = response.choices[0].message.parsed
            return merged

        except Exception as e:  # pylint: disable=broad-exception-caught
            console.print(f"[red]LLM merge failed: {e}[/red]")
            return metadata_list[0]

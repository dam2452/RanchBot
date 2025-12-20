import json
from typing import (
    List,
    Optional,
)

from openai import OpenAI
from pydantic import BaseModel

from preprocessor.config.config import settings
from preprocessor.utils.console import console


class EpisodeInfo(BaseModel):
    episode_number: int
    title: str
    premiere_date: str
    viewership: int


class SeasonMetadata(BaseModel):
    season_number: int
    episodes: List[EpisodeInfo]


class AllSeasonsMetadata(BaseModel):
    seasons: List[SeasonMetadata]


class EpisodeMetadata(BaseModel):
    title: str
    description: str
    summary: str
    season: Optional[int] = None
    episode_number: Optional[int] = None


class LLMProvider:
    BASE_URL = "http://localhost:11434/v1"
    API_KEY = "ollama"
    MODEL = "qwen3-coder-50k"

    def __init__(self, model: Optional[str] = None):
        self.base_url = self.BASE_URL
        self.api_key = self.API_KEY
        self.model = model or self.MODEL

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )

        console.print(f"[cyan]LLM Provider: Ollama (model: {self.model}, context: 50k)[/cyan]")

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

    def extract_all_seasons(self, scraped_pages: List[dict]) -> Optional[List[SeasonMetadata]]:
        system_prompt = """You are extracting episode data from multiple TV series pages.
Extract ALL episodes from ALL pages. Each page may contain one or multiple seasons.

For each episode extract:
- episode_number: integer
- title: string (clean title without markdown formatting)
- premiere_date: string (date format as found on page)
- viewership: integer (remove spaces from numbers like "4 396 564" -> 4396564, use 0 if not available)

Group episodes by season_number. Return ALL seasons found across ALL pages."""

        combined_content = ""
        for i, page in enumerate(scraped_pages, 1):
            url = page["url"]
            markdown = page["markdown"][:15000]
            combined_content += f"\n\n=== SOURCE {i}: {url} ===\n\n{markdown}\n"

        user_prompt = f"""Extract ALL episodes from ALL {len(scraped_pages)} sources below.
Return a complete list of ALL seasons found.

{combined_content}

Extract ALL seasons and episodes from above sources."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "AllSeasonsMetadata",
                        "strict": True,
                        "schema": AllSeasonsMetadata.model_json_schema(),
                    },
                },
            )

            content = response.choices[0].message.content
            data = json.loads(content)
            all_seasons_meta = AllSeasonsMetadata(**data)
            return all_seasons_meta.seasons

        except Exception as e:  # pylint: disable=broad-exception-caught
            console.print(f"[red]LLM extraction failed: {e}[/red]")
            return None

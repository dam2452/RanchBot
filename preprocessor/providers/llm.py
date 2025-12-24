import json
from pathlib import Path
from typing import List, Optional

import torch
from pydantic import BaseModel
from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from preprocessor.config.config import settings
from preprocessor.utils.console import console

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(name: str) -> str:
    prompt_file = PROMPTS_DIR / f"{name}.txt"
    return prompt_file.read_text(encoding="utf-8")


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
    MODEL_NAME = "Qwen/Qwen2.5-Coder-7B-Instruct"

    _instance = None
    _model = None
    _tokenizer = None

    def __new__(cls, model_name: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model_name: Optional[str] = None):
        if self._model is None:
            self.model_name = model_name or self.MODEL_NAME
            console.print(f"[cyan]Loading LLM: {self.model_name} (bitsandbytes 8-bit, 128K context)[/cyan]")

            try:
                self._tokenizer = AutoTokenizer.from_pretrained(
                    self.model_name,
                    trust_remote_code=True
                )

                config = AutoConfig.from_pretrained(
                    self.model_name,
                    trust_remote_code=True
                )
                config.rope_scaling = {
                    "type": "yarn",
                    "factor": 4.0,
                    "original_max_position_embeddings": 32768,
                }

                quantization_config = BitsAndBytesConfig(
                    load_in_8bit=True,
                )

                self._model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    config=config,
                    quantization_config=quantization_config,
                    device_map="auto",
                    trust_remote_code=True,
                )

                console.print(f"[green]✓ LLM loaded on {self._model.device}[/green]")
            except Exception as e:
                console.print(f"[red]Failed to load model: {e}[/red]")
                raise e

    def __generate(self, messages: List[dict], max_tokens: int = 32768) -> str:
        text = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        model_inputs = self._tokenizer([text], return_tensors="pt").to(self._model.device)

        with torch.inference_mode():
            generated_ids = self._model.generate(
                **model_inputs,
                max_new_tokens=max_tokens,
                temperature=0.7,
                top_p=0.8,
                top_k=20,
                repetition_penalty=1.05,
                do_sample=True,
            )

        output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist()
        content = self._tokenizer.decode(output_ids, skip_special_tokens=True)

        return content.strip()

    def __extract_json(self, content: str) -> dict:
        try:
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                json_str = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                json_str = content[start:end].strip()
            else:
                json_str = content.strip()

            return json.loads(json_str)
        except json.JSONDecodeError as e:
            console.print(f"[red]JSON parse error: {e}[/red]")
            console.print(f"[yellow]Raw content:\n{content}[/yellow]")
            raise

    def extract_season_episodes(self, page_text: str, url: str) -> Optional[SeasonMetadata]:
        system_prompt = load_prompt("extract_season_system")
        user_prompt = load_prompt("extract_season_user").format(url=url, page_text=page_text)

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            content = self._LLMProvider__generate(messages)
            data = self._LLMProvider__extract_json(content)
            metadata = SeasonMetadata(**data)
            return metadata

        except Exception as e:
            console.print(f"[red]LLM extraction failed for {url}: {e}[/red]")
            return None

    def extract_episode_metadata(self, page_text: str, url: str) -> Optional[EpisodeMetadata]:
        system_prompt = load_prompt("extract_episode_metadata_system")
        user_prompt = load_prompt("extract_episode_metadata_user").format(url=url, page_text=page_text)

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            content = self._LLMProvider__generate(messages)
            data = self._LLMProvider__extract_json(content)
            metadata = EpisodeMetadata(**data)
            return metadata

        except Exception as e:
            console.print(f"[red]LLM extraction failed for {url}: {e}[/red]")
            return None

    def merge_episode_data(self, metadata_list: List[EpisodeMetadata]) -> EpisodeMetadata:
        if not metadata_list:
            raise ValueError("No metadata to merge")

        if len(metadata_list) == 1:
            return metadata_list[0]

        combined_text = "\n\n---\n\n".join([
            f"Source {i + 1}:\nTitle: {m.title}\nDescription: {m.description}\nSummary: {m.summary}\nSeason: {m.season}\nEpisode: {m.episode_number}"
            for i, m in enumerate(metadata_list)
        ])

        system_prompt = load_prompt("merge_episode_data_system")
        user_prompt = load_prompt("merge_episode_data_user").format(
            num_sources=len(metadata_list),
            combined_text=combined_text
        )

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            content = self._LLMProvider__generate(messages)
            data = self._LLMProvider__extract_json(content)
            merged = EpisodeMetadata(**data)
            return merged

        except Exception as e:
            console.print(f"[red]LLM merge failed: {e}[/red]")
            return metadata_list[0]

    def extract_all_seasons(self, scraped_pages: List[dict]) -> Optional[List[SeasonMetadata]]:
        combined_content = ""
        for i, page in enumerate(scraped_pages, 1):
            url = page["url"]
            markdown = page["markdown"]
            combined_content += f"\n\n=== SOURCE {i}: {url} ===\n\n{markdown}\n"

        system_prompt = load_prompt("extract_all_seasons_system")
        user_prompt = load_prompt("extract_all_seasons_user").format(
            num_sources=len(scraped_pages),
            combined_content=combined_content
        )

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            content = self._LLMProvider__generate(messages)
            console.print(f"[yellow]LLM raw response:\n{content[:500]}...[/yellow]")
            data = self._LLMProvider__extract_json(content)
            all_seasons_meta = AllSeasonsMetadata(**data)
            return all_seasons_meta.seasons

        except Exception as e:
            console.print(f"[red]LLM extraction failed: {e}[/red]")
            console.print(f"[red]Full content:\n{content if 'content' in locals() else 'No content generated'}[/red]")
            return None

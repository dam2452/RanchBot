from __future__ import annotations

import json
import logging
from pathlib import Path
import random
import time
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
)

import cv2
from ddgs import DDGS
import numpy as np
import requests
import ua_generator

from preprocessor.characters.utils import init_face_detection

if TYPE_CHECKING:
    from insightface.app import FaceAnalysis
from preprocessor.config.config import settings
from preprocessor.core.base_processor import BaseProcessor
from preprocessor.utils.console import (
    console,
    create_progress,
)


class CharacterReferenceDownloader(BaseProcessor):
    def __init__(self, args: Dict[str, Any]):
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=8,
            loglevel=logging.DEBUG,
        )

        self.characters_json: Path = self._args["characters_json"]
        self.series_name: str = self._args["series_name"]
        self.output_dir: Path = self._args.get("output_dir", settings.character.output_dir)
        self.images_per_character: int = self._args.get(
            "images_per_character",
            settings.character.reference_images_per_character,
        )
        self.max_results: int = settings.face_recognition.max_results_to_scrape
        self.min_width: int = settings.face_recognition.min_image_width
        self.min_height: int = settings.face_recognition.min_image_height
        self.use_gpu: bool = settings.face_recognition.use_gpu

        self.face_app: FaceAnalysis = None

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if "characters_json" not in args:
            raise ValueError("characters_json is required")
        if "series_name" not in args:
            raise ValueError("series_name is required")

    def _execute(self) -> None:
        if not self.characters_json.exists():
            console.print(f"[red]Characters JSON not found: {self.characters_json}[/red]")
            return

        with open(self.characters_json, encoding="utf-8") as f:
            data = json.load(f)

        characters = data.get("characters", [])
        if not characters:
            console.print("[yellow]No characters found in JSON[/yellow]")
            return

        self.face_app = init_face_detection(self.use_gpu)

        console.print(f"[blue]Downloading reference images for {len(characters)} characters...[/blue]")

        with create_progress() as progress:
            task = progress.add_task("Downloading references", total=len(characters))

            for i, char in enumerate(characters):
                char_name = char["name"]
                try:
                    self._download_character_references(char_name, progress)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    self.logger.error(f"Failed to download references for {char_name}: {e}")
                finally:
                    progress.advance(task)

                if i < len(characters) - 1:
                    delay = random.uniform(
                        settings.face_recognition.request_delay_min,
                        settings.face_recognition.request_delay_max,
                    )
                    time.sleep(delay)

        console.print("[green]✓ Reference download completed[/green]")

    def _count_faces(self, img) -> int:
        faces = self.face_app.get(img)
        return len(faces)

    def _download_character_references(self, char_name: str, progress):  # pylint: disable=too-many-locals,too-many-statements
        search_query = f"Serial {self.series_name} {char_name} postać"
        output_folder = self.output_dir / char_name.replace(" ", "_").lower()
        output_folder.mkdir(parents=True, exist_ok=True)

        progress.console.print(f"[cyan]Searching: {search_query}[/cyan]")

        ua = ua_generator.generate()
        headers = {'User-Agent': str(ua)}
        saved_count = 0
        processed = 0

        for attempt in range(settings.face_recognition.retry_attempts):
            try:
                with DDGS() as ddgs:
                    results = ddgs.images(search_query, max_results=self.max_results)

                    for res in results:
                        if saved_count >= self.images_per_character:
                            break

                        img_url = res['image']
                        processed += 1

                        try:  # pylint: disable=too-many-try-statements
                            response = requests.get(img_url, headers=headers, timeout=5)
                            if response.status_code != 200:
                                continue

                            img_array = np.asarray(bytearray(response.content), dtype=np.uint8)
                            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                            if img is None:
                                continue

                            h, w = img.shape[:2]
                            if w < self.min_width or h < self.min_height:
                                continue

                            face_count = self._count_faces(img)

                            if face_count == 1:
                                filename = f"{saved_count:02d}.jpg"
                                path = output_folder / filename
                                cv2.imwrite(str(path), img)
                                saved_count += 1

                        except (requests.exceptions.Timeout, requests.exceptions.RequestException):
                            continue
                        except Exception as e:  # pylint: disable=broad-exception-caught
                            self.logger.debug(f"Error processing image: {e}")
                            continue

                break

            except KeyboardInterrupt:
                progress.console.print("\n[yellow]Download interrupted[/yellow]")
                raise
            except Exception as e:  # pylint: disable=broad-exception-caught
                if attempt < settings.face_recognition.retry_attempts - 1:
                    delay = settings.face_recognition.retry_delay * (2 ** attempt)
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed for {char_name}, retrying in {delay}s: {e}",
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(f"All retry attempts failed for {char_name}: {e}")

        if saved_count > 0:
            progress.console.print(
                f"[green]✓[/green] {char_name}: {saved_count}/{self.images_per_character} images",
            )
        else:
            progress.console.print(f"[yellow]⚠[/yellow] {char_name}: No suitable images found")

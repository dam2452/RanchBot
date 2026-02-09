from __future__ import annotations

import json
import logging
from pathlib import Path
import random
import time
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import cv2
from insightface.app import FaceAnalysis
import numpy as np
from patchright.sync_api import (
    BrowserContext,
    Page,
    sync_playwright,
)

from preprocessor.characters.face_detection import init_face_detection
from preprocessor.characters.image_search import BaseImageSearch
from preprocessor.characters.duckduckgo_image_search import DuckDuckGoImageSearch
from preprocessor.characters.google_image_search import GoogleImageSearch
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
        self.output_dir: Path = self._args.get("output_dir", settings.character.get_output_dir(self.series_name))
        self.images_per_character: int = self._args.get(
            "images_per_character",
            settings.character.reference_images_per_character,
        )
        self.max_results: int = settings.image_scraper.max_results_to_scrape
        self.min_width: int = settings.image_scraper.min_image_width
        self.min_height: int = settings.image_scraper.min_image_height
        self.use_gpu: bool = True
        self.search_mode: str = self._args.get("search_mode", "normal")

        self.search_engine: BaseImageSearch = self.__create_search_engine()
        self.face_app: FaceAnalysis = None
        self.browser_context: Optional[BrowserContext] = None

    def __create_search_engine(self) -> BaseImageSearch:
        if self.search_mode == "premium":
            serpapi_key = settings.image_scraper.serpapi_key
            return GoogleImageSearch(api_key=serpapi_key, max_results=self.max_results)
        return DuckDuckGoImageSearch(max_results=self.max_results)

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if "characters_json" not in args:
            raise ValueError("characters_json is required")

    def get_output_subdir(self) -> str:
        return "character_references"
        if "series_name" not in args:
            raise ValueError("series_name is required")

    def __all_references_exist(self, characters: List[Dict[str, Any]]) -> bool:
        for char in characters:
            char_name = char["name"]
            output_folder = self.output_dir / char_name.replace(" ", "_").lower()
            existing_images = list(output_folder.glob("*.jpg"))
            if len(existing_images) < self.images_per_character:
                return False
        return True

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

        if self.__all_references_exist(characters):
            console.print(f"[green]✓ All reference images already exist for {len(characters)} characters (skipping)[/green]")
            return

        self.face_app = init_face_detection()

        console.print(f"[blue]Downloading reference images for {len(characters)} characters...[/blue]")

        with sync_playwright() as p:
            self.browser_context = p.chromium.launch_persistent_context(
                user_data_dir="/tmp/patchright_profile",
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                ],
                ignore_default_args=['--enable-automation'],
            )

            with create_progress() as progress:
                task = progress.add_task("Downloading references", total=len(characters))

                for i, char in enumerate(characters):
                    char_name = char["name"]
                    downloaded = False
                    try:
                        downloaded = self.__download_character_references(char_name, progress)
                    except Exception as e:
                        self.logger.error(f"Failed to download references for {char_name}: {e}")
                    finally:
                        progress.advance(task)

                    if downloaded and i < len(characters) - 1:
                        delay = random.uniform(
                            settings.image_scraper.request_delay_min,
                            settings.image_scraper.request_delay_max,
                        )
                        time.sleep(delay)

            self.browser_context.close()

        console.print("[green]✓ Reference download completed[/green]")

    def __count_faces(self, img) -> int:
        faces = self.face_app.get(img)
        return len(faces)

    def _validate_and_decode_image(self, img_bytes: bytes, img_url: str) -> np.ndarray | None:
        if not img_bytes:
            return None

        img_array = np.asarray(bytearray(img_bytes), dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if img is None or img.size == 0:
            self.logger.debug(f"Failed to decode image from {img_url}")
            return None

        if len(img.shape) != 3 or img.shape[2] != 3:
            self.logger.debug(f"Image has unexpected shape {img.shape} from {img_url}")
            return None

        return img

    def __download_image_with_browser(self, img_url: str, page: Page) -> np.ndarray | None:
        try:  # pylint: disable=too-many-try-statements
            response = page.goto(
                img_url,
                timeout=settings.image_scraper.page_navigation_timeout,
                wait_until="domcontentloaded",
            )
            if not response or response.status != 200:
                return None

            content_type = response.headers.get("content-type", "")
            if "image" not in content_type:
                return None

            img_bytes = response.body()
            if not img_bytes:
                return None

            img_array = np.asarray(bytearray(img_bytes), dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            if img is None or img.size == 0:
                self.logger.debug(f"Failed to decode image from {img_url}")
                return None

            if len(img.shape) != 3 or img.shape[2] != 3:
                self.logger.debug(f"Image has unexpected shape {img.shape} from {img_url}")
                return None

            return img

        except TimeoutError:
            self.logger.debug(f"Timeout downloading image {img_url}")
            return None
        except Exception as e:
            if "net::ERR_CONNECTION_CLOSED" in str(e) or "Navigation" in str(e):
                self.logger.debug(f"Connection/navigation error for {img_url}: {e}")
            else:
                self.logger.debug(f"Failed to download image {img_url}: {e}")
            return None

    def __download_character_references(self, char_name: str, progress) -> bool:  # pylint: disable=too-many-locals,too-many-statements
        search_query = f"Serial {self.series_name} {char_name} postać"
        output_folder = self.output_dir / char_name.replace(" ", "_").lower()
        output_folder.mkdir(parents=True, exist_ok=True)

        existing_images = list(output_folder.glob("*.jpg"))
        if len(existing_images) >= self.images_per_character:
            progress.console.print(
                f"[green]✓ {char_name}: {len(existing_images)} images already exist (skipping)[/green]",
            )
            return False

        progress.console.print(f"[cyan]Searching [{self.search_engine.name}]: {search_query}[/cyan]")

        saved_count = len(existing_images)
        processed = 0

        for attempt in range(settings.image_scraper.retry_attempts):  # pylint: disable=too-many-nested-blocks
            try:
                results = self.search_engine.search(search_query)

                sorted_results = sorted(
                    results,
                    key=lambda x: (
                        0 if x.get('image', '').lower().endswith(('.jpg', '.jpeg')) else 1,
                        1 if x.get('image', '').lower().endswith('.png') else 2,
                    ),
                )

                page = self.browser_context.new_page()

                try:
                    for res in sorted_results:
                        if saved_count >= self.images_per_character:
                            break

                        img_url = res['image']
                        processed += 1

                        try:
                            img = self.__download_image_with_browser(img_url, page)

                            if img is None:
                                continue

                            if not isinstance(img, np.ndarray) or img.size == 0:
                                self.logger.debug(f"Invalid image array from {img_url}")
                                continue

                            h, w = img.shape[:2]
                            if w < self.min_width or h < self.min_height:
                                continue

                            try:
                                face_count = self.__count_faces(img)
                            except Exception as face_err:
                                self.logger.debug(f"Face detection failed for {img_url}: {face_err}")
                                continue

                            if face_count == 1:
                                filename = f"{saved_count:02d}.jpg"
                                path = output_folder / filename
                                cv2.imwrite(str(path), img)
                                saved_count += 1

                        except Exception as e:
                            self.logger.debug(f"Error processing image: {e}")
                            continue

                finally:
                    page.close()

                break

            except KeyboardInterrupt:
                progress.console.print("\n[yellow]Download interrupted[/yellow]")
                raise
            except Exception as e:
                if attempt < settings.image_scraper.retry_attempts - 1:
                    delay = settings.image_scraper.retry_delay * (2 ** attempt)
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed for {char_name}, retrying in {delay}s: {e}",
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(f"All retry attempts failed for {char_name}: {e}")

        if saved_count >= self.images_per_character:
            progress.console.print(
                f"[green]✓[/green] {char_name}: {saved_count}/{self.images_per_character} images",
            )
        elif saved_count > 0:
            progress.console.print(
                f"[yellow]⚠[/yellow] {char_name}: {saved_count}/{self.images_per_character} images (incomplete)",
            )
        else:
            progress.console.print(f"[red]✗[/red] {char_name}: No suitable images found")

        return True

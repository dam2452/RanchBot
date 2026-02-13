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
    Playwright,
    sync_playwright,
)

from preprocessor.config.settings_instance import settings
from preprocessor.services.characters.face_detection import FaceDetector
from preprocessor.services.characters.image_search import (
    BaseImageSearch,
    DuckDuckGoImageSearch,
    GoogleImageSearch,
)
from preprocessor.services.core.base_processor import (
    BaseProcessor,
    OutputSpec,
    ProcessingItem,
)
from preprocessor.services.ui.console import console


class CharacterReferenceDownloader(BaseProcessor):
    def __init__(self, args: Dict[str, Any]) -> None:
        super().__init__(
            args=args,
            class_name=self.__class__.__name__,
            error_exit_code=8,
            loglevel=logging.DEBUG,
        )
        self.__characters_json: Path = self._args['characters_json']
        self.__series_name: str = self._args['series_name']
        self.__output_dir: Path = self._args.get(
            'output_dir', settings.character.get_output_dir(self.__series_name),
        )
        self.__images_per_character: int = self._args.get(
            'images_per_character', settings.character.reference_images_per_character,
        )

        self.__max_results: int = settings.image_scraper.max_results_to_scrape
        self.__min_width: int = settings.image_scraper.min_image_width
        self.__min_height: int = settings.image_scraper.min_image_height
        self.__search_mode: str = self._args.get('search_mode', 'normal')

        self.__search_engine: BaseImageSearch = self.__create_search_engine()
        self.__face_app: Optional[FaceAnalysis] = None
        self.__playwright: Optional[Playwright] = None
        self.__browser_context: Optional[BrowserContext] = None

    def get_output_subdir(self) -> str:
        return 'character_references'

    def cleanup(self) -> None:
        if self.__browser_context:
            self.__browser_context.close()
        if self.__playwright:
            self.__playwright.stop()

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if 'characters_json' not in args:
            raise ValueError("Argument 'characters_json' is required.")

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        char_name = item.metadata['char_name']
        output_folder = self.__output_dir / char_name.replace(' ', '_').lower()

        return [
            OutputSpec(path=output_folder / f'{i:02d}.jpg', required=True)
            for i in range(self.__images_per_character)
        ]

    def _get_processing_items(self) -> List[ProcessingItem]:
        if not self.__characters_json.exists():
            console.print(f'[red]Characters JSON not found: {self.__characters_json}[/red]')
            return []

        with open(self.__characters_json, encoding='utf-8') as f:
            data = json.load(f)

        return [
            ProcessingItem(
                episode_id=f"char_{char['name']}",
                input_path=self.__characters_json,
                metadata={'char_name': char['name']},
            )
            for char in data.get('characters', [])
        ]

    def _load_resources(self) -> bool:
        self.__face_app = FaceDetector.init()
        self.__playwright = sync_playwright().start()
        self.__browser_context = self.__playwright.chromium.launch_persistent_context(
            user_data_dir='/tmp/patchright_profile',
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
            ignore_default_args=['--enable-automation'],
        )
        return True

    def _process_item(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> None:
        char_name = item.metadata['char_name']
        output_folder = self.__prepare_output_folder(char_name)

        saved_count = len(list(output_folder.glob('*.jpg')))
        if saved_count >= self.__images_per_character:
            return

        search_query = f'Serial {self.__series_name} {char_name} postać'
        self.logger.info(f'Searching [{self.__search_engine.name}]: {search_query}')

        saved_count = self.__execute_search_with_retries(search_query, char_name, output_folder, saved_count)
        self.__log_final_results(char_name, saved_count)
        self.__apply_random_delay()


    def __create_search_engine(self) -> BaseImageSearch:
        if self.__search_mode == 'premium':
            return GoogleImageSearch(
                api_key=settings.image_scraper.serpapi_key,
                max_results=self.__max_results,
            )
        return DuckDuckGoImageSearch(max_results=self.__max_results)

    def __prepare_output_folder(self, char_name: str) -> Path:
        output_folder = self.__output_dir / char_name.replace(' ', '_').lower()
        output_folder.mkdir(parents=True, exist_ok=True)
        return output_folder

    def __execute_search_with_retries(
            self, query: str, char_name: str, output_folder: Path, saved_count: int,
    ) -> int:
        for attempt in range(settings.image_scraper.retry_attempts):
            try:
                results = self.__search_engine.search(query)
                return self.__download_and_process_images(results, output_folder, saved_count)
            except Exception as e:
                if isinstance(e, KeyboardInterrupt):
                    raise
                self.__handle_retry_logic(e, attempt, char_name)
        return saved_count

    def __handle_retry_logic(self, error: Exception, attempt: int, char_name: str) -> None:
        if attempt < settings.image_scraper.retry_attempts - 1:
            delay = settings.image_scraper.retry_delay * (2 ** attempt)
            self.logger.warning(f'Attempt {attempt + 1} failed for {char_name}, retrying in {delay}s: {error}')
            time.sleep(delay)
        else:
            self.logger.error(f'All retry attempts failed for {char_name}: {error}')

    def __download_and_process_images(
            self, results: List[Dict[str, Any]], output_folder: Path, saved_count: int,
    ) -> int:
        sorted_results = self.__sort_results_by_extension(results)

        page = self.__browser_context.new_page()
        try:
            for res in sorted_results:
                if saved_count >= self.__images_per_character:
                    break

                img_url = res.get('image', '')
                try:
                    img = self.__download_image_via_browser(img_url, page)
                    if img is not None and self.__validate_and_save_image(img, img_url, output_folder, saved_count):
                        saved_count += 1
                except Exception as e:
                    self.logger.debug(f'Error processing image {img_url}: {e}')
        finally:
            page.close()

        return saved_count

    def __download_image_via_browser(self, img_url: str, page: Page) -> Optional[np.ndarray]:
        try:
            response = page.goto(
                img_url,
                timeout=settings.image_scraper.page_navigation_timeout,
                wait_until='domcontentloaded',
            )

            if not response or response.status != 200:
                return None

            if 'image' not in response.headers.get('content-type', ''):
                return None

            return self.__decode_image_bytes(response.body(), img_url)

        except TimeoutError:
            self.logger.debug(f'Timeout downloading image {img_url}')
        except Exception as e:
            msg = str(e)
            if 'net::ERR_CONNECTION_CLOSED' in msg or 'Navigation' in msg:
                self.logger.debug(f'Connection/navigation error for {img_url}: {msg}')
            else:
                self.logger.debug(f'Failed to download image {img_url}: {msg}')
        return None

    def __decode_image_bytes(self, img_bytes: bytes, img_url: str) -> Optional[np.ndarray]:
        if not img_bytes:
            return None

        img_array = np.asarray(bytearray(img_bytes), dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if img is None or img.size == 0:
            self.logger.debug(f'Failed to decode image from {img_url}')
            return None

        if len(img.shape) != 3 or img.shape[2] != 3:
            self.logger.debug(f'Image has unexpected shape {img.shape} from {img_url}')
            return None

        return img

    def __validate_and_save_image(
            self, img: np.ndarray, img_url: str, output_folder: Path, saved_count: int,
    ) -> bool:
        h, w = img.shape[:2]
        if w < self.__min_width or h < self.__min_height:
            return False

        try:
            face_count = len(self.__face_app.get(img))
        except Exception as face_err:
            self.logger.debug(f'Face detection failed for {img_url}: {face_err}')
            return False

        if face_count != 1:
            return False

        filename = f'{saved_count:02d}.jpg'
        cv2.imwrite(str(output_folder / filename), img)
        return True

    @staticmethod
    def __sort_results_by_extension(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(
            results,
            key=lambda x: (
                0 if x.get('image', '').lower().endswith(('.jpg', '.jpeg')) else 1,
                1 if x.get('image', '').lower().endswith('.png') else 2,
            ),
        )

    def __log_final_results(self, char_name: str, saved_count: int) -> None:
        if saved_count >= self.__images_per_character:
            self.logger.info(f'{char_name}: {saved_count}/{self.__images_per_character} images')
        elif saved_count > 0:
            self.logger.warning(f'{char_name}: {saved_count}/{self.__images_per_character} images (incomplete)')
        else:
            self.logger.error(f'{char_name}: No suitable images found')

    @staticmethod
    def __apply_random_delay() -> None:
        delay = random.uniform(
            settings.image_scraper.request_delay_min,
            settings.image_scraper.request_delay_max,
        )
        time.sleep(delay)

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

from preprocessor.config.config import settings
from preprocessor.lib.characters.face_detection import FaceDetector
from preprocessor.lib.characters.image_search import (
    BaseImageSearch,
    DuckDuckGoImageSearch,
    GoogleImageSearch,
)
from preprocessor.lib.ui.console import console
from preprocessor.modules.base_processor import (
    BaseProcessor,
    OutputSpec,
    ProcessingItem,
)


class CharacterReferenceDownloader(BaseProcessor):

    def __init__(self, args: Dict[str, Any]):
        super().__init__(args=args, class_name=self.__class__.__name__, error_exit_code=8, loglevel=logging.DEBUG)
        self.characters_json: Path = self._args['characters_json']
        self.series_name: str = self._args['series_name']
        self.output_dir: Path = self._args.get('output_dir', settings.character.get_output_dir(self.series_name))
        self.images_per_character: int = self._args.get('images_per_character', settings.character.reference_images_per_character)
        self.max_results: int = settings.image_scraper.max_results_to_scrape
        self.min_width: int = settings.image_scraper.min_image_width
        self.min_height: int = settings.image_scraper.min_image_height
        self.use_gpu: bool = True
        self.search_mode: str = self._args.get('search_mode', 'normal')
        self.search_engine: BaseImageSearch = self.__create_search_engine()
        self.face_app: Optional[FaceAnalysis] = None
        self.playwright: Optional[Playwright] = None
        self.browser_context: Optional[BrowserContext] = None

    def cleanup(self) -> None:
        if self.browser_context:
            self.browser_context.close()
        if self.playwright:
            self.playwright.stop()

    def get_output_subdir(self) -> str:
        return 'character_references'

    def _get_expected_outputs(self, item: ProcessingItem) -> List[OutputSpec]:
        char_name = item.metadata['char_name']
        output_folder = self.output_dir / char_name.replace(' ', '_').lower()
        expected_files = [
            OutputSpec(path=output_folder / f'{i:02d}.jpg', required=True)
            for i in range(self.images_per_character)
        ]
        return expected_files

    def _get_processing_items(self) -> List[ProcessingItem]:
        if not self.characters_json.exists():
            console.print(f'[red]Characters JSON not found: {self.characters_json}[/red]')
            return []
        with open(self.characters_json, encoding='utf-8') as f:
            data = json.load(f)
        characters = data.get('characters', [])
        return [
            ProcessingItem(
                episode_id=f"char_{char['name']}",
                input_path=self.characters_json,
                metadata={'char_name': char['name']},
            )
            for char in characters
        ]

    def _load_resources(self) -> bool:
        self.face_app = FaceDetector.init()
        self.playwright = sync_playwright().start()
        self.browser_context = self.playwright.chromium.launch_persistent_context(
            user_data_dir='/tmp/patchright_profile',
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
            ignore_default_args=['--enable-automation'],
        )
        return True

    def _process_item(self, item: ProcessingItem, missing_outputs: List[OutputSpec]) -> None:
        char_name = item.metadata['char_name']
        output_folder = self.__prepare_output_folder(char_name)
        existing_images = list(output_folder.glob('*.jpg'))
        saved_count = len(existing_images)
        if saved_count >= self.images_per_character:
            return
        search_query = f'Serial {self.series_name} {char_name} postać'
        self.logger.info(f'Searching [{self.search_engine.name}]: {search_query}')
        for attempt in range(settings.image_scraper.retry_attempts):
            try:
                results = self.search_engine.search(search_query)
                saved_count = self.__process_search_results(results, output_folder, saved_count)
                break
            except KeyboardInterrupt:  # pylint: disable=try-except-raise
                raise
            except Exception as e:
                if attempt < settings.image_scraper.retry_attempts - 1:
                    delay = settings.image_scraper.retry_delay * 2 ** attempt
                    self.logger.warning(
                        f'Attempt {attempt + 1} failed for {char_name}, retrying in {delay}s: {e}',
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(f'All retry attempts failed for {char_name}: {e}')
        self.__log_results(char_name, saved_count)
        delay = random.uniform(
            settings.image_scraper.request_delay_min,
            settings.image_scraper.request_delay_max,
        )
        time.sleep(delay)

    def _validate_args(self, args: Dict[str, Any]) -> None:
        if 'characters_json' not in args:
            raise ValueError('characters_json is required')


    def __count_faces(self, img) -> int:
        faces = self.face_app.get(img)
        return len(faces)

    def __create_search_engine(self) -> BaseImageSearch:
        if self.search_mode == 'premium':
            serpapi_key = settings.image_scraper.serpapi_key
            return GoogleImageSearch(api_key=serpapi_key, max_results=self.max_results)
        return DuckDuckGoImageSearch(max_results=self.max_results)


    def __download_image_with_browser(
        self, img_url: str, page: Page,
    ) -> np.ndarray | None:
        try:
            response = page.goto(
                img_url,
                timeout=settings.image_scraper.page_navigation_timeout,
                wait_until='domcontentloaded',
            )
            if not response or response.status != 200:
                return None
            content_type = response.headers.get('content-type', '')
            if 'image' not in content_type:
                return None
            img_bytes = response.body()
            return self.__validate_and_decode_image(img_bytes, img_url, self.logger)
        except TimeoutError:
            self.logger.debug(f'Timeout downloading image {img_url}')
            return None
        except Exception as e:
            if 'net::ERR_CONNECTION_CLOSED' in str(e) or 'Navigation' in str(e):
                self.logger.debug(
                    f'Connection/navigation error for {img_url}: {e}',
                )
            else:
                self.logger.debug(f'Failed to download image {img_url}: {e}')
            return None

    def __prepare_output_folder(self, char_name: str) -> Path:
        output_folder = self.output_dir / char_name.replace(' ', '_').lower()
        output_folder.mkdir(parents=True, exist_ok=True)
        return output_folder

    def __log_results(self, char_name: str, saved_count: int) -> None:
        if saved_count >= self.images_per_character:
            self.logger.info(
                f'{char_name}: {saved_count}/{self.images_per_character} images',
            )
        elif saved_count > 0:
            self.logger.warning(
                f'{char_name}: {saved_count}/{self.images_per_character} images (incomplete)',
            )
        else:
            self.logger.error(f'{char_name}: No suitable images found')

    def __process_search_results(
        self, results: List[Dict[str, Any]], output_folder: Path, saved_count: int,
    ) -> int:
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
                try:
                    img = self.__download_image_with_browser(img_url, page)
                    if img is None:
                        continue
                    if self.__validate_and_save_image(
                        img, img_url, output_folder, saved_count,
                    ):
                        saved_count += 1
                except Exception as e:
                    self.logger.debug(f'Error processing image: {e}')
                    continue
        finally:
            page.close()
        return saved_count

    @staticmethod
    def __validate_and_decode_image(
        img_bytes: bytes, img_url: str, logger,
    ) -> np.ndarray | None:
        if not img_bytes:
            return None
        img_array = np.asarray(bytearray(img_bytes), dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None or img.size == 0:
            logger.debug(f'Failed to decode image from {img_url}')
            return None
        if len(img.shape) != 3 or img.shape[2] != 3:
            logger.debug(f'Image has unexpected shape {img.shape} from {img_url}')
            return None
        return img

    def __validate_and_save_image(
        self, img: np.ndarray, img_url: str, output_folder: Path, saved_count: int,
    ) -> bool:
        if not isinstance(img, np.ndarray) or img.size == 0:
            self.logger.debug(f'Invalid image array from {img_url}')
            return False
        h, w = img.shape[:2]
        if w < self.min_width or h < self.min_height:
            return False
        try:
            face_count = self.__count_faces(img)
        except Exception as face_err:
            self.logger.debug(f'Face detection failed for {img_url}: {face_err}')
            return False
        if face_count != 1:
            return False
        filename = f'{saved_count:02d}.jpg'
        path = output_folder / filename
        cv2.imwrite(str(path), img)
        return True

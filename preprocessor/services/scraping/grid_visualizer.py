from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

import cv2
import numpy as np

from preprocessor.config.settings_instance import settings


@dataclass
class GridDimensions:
    face_size: int = 280
    faces_per_char: int = 3
    footer_height: int = 80
    header_height: int = 180
    header_row_height: int = 40
    label_col_width: int = 350
    padding: int = 15
    stats_col_width: int = 200

    @property
    def face_col_width(self) -> int:
        return self.face_size + self.padding

    @property
    def row_height(self) -> int:
        return self.face_size + self.padding * 2

    def total_height(self, num_chars: int) -> int:
        return self.header_height + num_chars * self.row_height + self.footer_height

    def total_width(self) -> int:
        return (
            self.label_col_width
            + self.stats_col_width
            + self.faces_per_char * self.face_col_width
            + self.padding * 2
        )


class CharacterGridVisualizer:
    def __init__(
        self,
        dimensions: Optional[GridDimensions] = None,
        similarity_threshold: float = 0.5,
    ) -> None:
        self._dims = dimensions or GridDimensions()
        self._similarity_threshold = similarity_threshold

    def generate_grid(
        self,
        processed_chars_dir: Path,
        output_path: Path,
    ) -> Dict[str, Any]:
        processed_chars = sorted([d for d in processed_chars_dir.iterdir() if d.is_dir()])

        if not processed_chars:
            return {
                'width': 0,
                'height': 0,
                'num_chars': 0,
                'avg_similarity': 0.0,
            }

        canvas = self.__create_canvas(processed_chars)
        metadata_all = self.__load_all_metadata(processed_chars)
        avg_similarity = self.__calculate_avg_similarity(metadata_all)

        canvas = self.__render_header(canvas, len(processed_chars), avg_similarity)
        canvas = self.__render_table_headers(canvas)
        canvas = self.__render_character_rows(canvas, processed_chars)
        canvas = self.__render_footer(canvas)

        cv2.imwrite(
            str(output_path),
            canvas,
            [cv2.IMWRITE_PNG_COMPRESSION, 6],
        )

        return {
            'width': self._dims.total_width(),
            'height': self._dims.total_height(len(processed_chars)),
            'num_chars': len(processed_chars),
            'avg_similarity': avg_similarity,
        }

    def __create_canvas(self, processed_chars: List[Path]) -> np.ndarray:
        grid_width = self._dims.total_width()
        grid_height = self._dims.total_height(len(processed_chars))
        bg_color = (250, 252, 255)
        return np.full((grid_height, grid_width, 3), bg_color, dtype=np.uint8)

    def __render_header(
        self,
        canvas: np.ndarray,
        total_chars: int,
        avg_similarity: float,
    ) -> np.ndarray:
        header_bg_color = (45, 55, 72)
        cv2.rectangle(
            canvas,
            (0, 0),
            (self._dims.total_width(), self._dims.header_height),
            header_bg_color,
            -1,
        )

        title_text = 'FACIAL REFERENCE VALIDATION REPORT'
        cv2.putText(
            canvas,
            title_text,
            (self._dims.padding * 3, 50),
            cv2.FONT_HERSHEY_DUPLEX,
            1.1,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        subtitle = 'InsightFace Buffalo-L Model | Face Vector Extraction & Similarity Analysis'
        cv2.putText(
            canvas,
            subtitle,
            (self._dims.padding * 3, 85),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (200, 210, 220),
            1,
            cv2.LINE_AA,
        )

        stats_y = 115
        stats_items = [
            f'Total Subjects: {total_chars}',
            f'Avg Similarity: {avg_similarity:.4f}',
            f'Threshold: {self._similarity_threshold:.2f}',
        ]
        for idx, stat in enumerate(stats_items):
            x_pos = self._dims.padding * 3 + idx * 280
            cv2.putText(
                canvas,
                stat,
                (x_pos, stats_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (180, 200, 220),
                1,
                cv2.LINE_AA,
            )

        return canvas

    def __render_table_headers(self, canvas: np.ndarray) -> np.ndarray:
        table_header_y = self._dims.header_height + 1
        cv2.line(
            canvas,
            (0, table_header_y),
            (self._dims.total_width(), table_header_y),
            (180, 190, 200),
            2,
        )

        col_headers = [
            ('CHARACTER NAME', self._dims.label_col_width // 2, 0),
            ('STATISTICS', self._dims.label_col_width + self._dims.stats_col_width // 2, 0),
            (
                'REFERENCE IMAGE 1',
                self._dims.label_col_width + self._dims.stats_col_width + self._dims.face_col_width // 2,
                0,
            ),
            (
                'REFERENCE IMAGE 2',
                self._dims.label_col_width + self._dims.stats_col_width + self._dims.face_col_width * 3 // 2,
                0,
            ),
            (
                'REFERENCE IMAGE 3',
                self._dims.label_col_width + self._dims.stats_col_width + self._dims.face_col_width * 5 // 2,
                0,
            ),
        ]

        for text, x_center, _ in col_headers:
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)[0]
            text_x = x_center - text_size[0] // 2
            cv2.putText(
                canvas,
                text,
                (text_x, table_header_y + 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42,
                (60, 70, 85),
                1,
                cv2.LINE_AA,
            )

        cv2.line(
            canvas,
            (0, table_header_y + self._dims.header_row_height),
            (self._dims.total_width(), table_header_y + self._dims.header_row_height),
            (200, 210, 220),
            1,
        )

        return canvas

    def __render_character_rows(
        self,
        canvas: np.ndarray,
        processed_chars: List[Path],
    ) -> np.ndarray:
        y_offset = self._dims.header_height + self._dims.header_row_height + self._dims.padding
        bg_color = (250, 252, 255)

        for idx, char_dir in enumerate(processed_chars):
            self.__render_character_row(canvas, char_dir, idx, y_offset, bg_color)
            y_offset += self._dims.row_height

        return canvas

    def __render_character_row(
        self,
        canvas: np.ndarray,
        char_dir: Path,
        row_idx: int,
        y_offset: int,
        bg_color: Tuple[int, int, int],
    ) -> None:
        char_name = char_dir.name.replace('_', ' ').title()
        row_bg = (245, 248, 252) if row_idx % 2 == 0 else bg_color

        cv2.rectangle(
            canvas,
            (0, y_offset - self._dims.padding),
            (self._dims.total_width(), y_offset + self._dims.face_size + self._dims.padding),
            row_bg,
            -1,
        )

        cv2.putText(
            canvas,
            char_name,
            (self._dims.padding * 2, y_offset + self._dims.face_size // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (30, 40, 50),
            1,
            cv2.LINE_AA,
        )

        self.__render_character_stats(canvas, char_dir, y_offset)
        self.__render_character_faces(canvas, char_dir, y_offset)

    def __render_character_stats(
        self,
        canvas: np.ndarray,
        char_dir: Path,
        y_offset: int,
    ) -> None:
        metadata_file = char_dir / 'metadata.json'
        if not metadata_file.exists():
            return

        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        similarity = metadata.get('average_similarity', 0.0)
        method = metadata.get('detection_stats', {}).get('selection_method', 'unknown')
        faces_detected = metadata.get('detection_stats', {}).get('total_faces_detected', [])

        stats_x = self._dims.label_col_width + self._dims.padding
        stats_y_base = y_offset + self._dims.face_size // 2 - 30

        sim_color = (0, 150, 0) if similarity >= self._similarity_threshold else (180, 100, 0)
        cv2.putText(
            canvas,
            f'Similarity: {similarity:.4f}',
            (stats_x, stats_y_base),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            sim_color,
            1,
            cv2.LINE_AA,
        )

        method_color = (50, 120, 200) if method == 'automatic' else (180, 100, 50)
        cv2.putText(
            canvas,
            f'Method: {method}',
            (stats_x, stats_y_base + 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            method_color,
            1,
            cv2.LINE_AA,
        )

        faces_str = str(faces_detected) if len(str(faces_detected)) < 20 else f'[{len(faces_detected)} imgs]'
        cv2.putText(
            canvas,
            f'Detected: {faces_str}',
            (stats_x, stats_y_base + 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.38,
            (100, 110, 120),
            1,
            cv2.LINE_AA,
        )

    def __render_character_faces(
        self,
        canvas: np.ndarray,
        char_dir: Path,
        y_offset: int,
    ) -> None:
        face_files = sorted(char_dir.glob('face_*.jpg'))
        for face_idx, face_file in enumerate(face_files[:self._dims.faces_per_char]):
            face_img = cv2.imread(str(face_file))
            if face_img is None:
                continue

            face_resized = self._safe_resize(face_img, (self._dims.face_size, self._dims.face_size))
            if face_resized is None:
                continue

            x = (
                self._dims.label_col_width
                + self._dims.stats_col_width
                + face_idx * self._dims.face_col_width
                + self._dims.padding
            )
            canvas[y_offset:y_offset + self._dims.face_size, x:x + self._dims.face_size] = face_resized

            cv2.rectangle(
                canvas,
                (x - 1, y_offset - 1),
                (x + self._dims.face_size + 1, y_offset + self._dims.face_size + 1),
                (180, 190, 200),
                1,
            )

    def __render_footer(self, canvas: np.ndarray) -> np.ndarray:
        grid_height = canvas.shape[0]
        footer_y = grid_height - self._dims.footer_height + 20
        cv2.line(
            canvas,
            (0, footer_y - 20),
            (self._dims.total_width(), footer_y - 20),
            (200, 210, 220),
            1,
        )

        footer_text = (
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            f"Model: {settings.face_recognition.model_name} | "
            f"Normalized Size: {settings.character.normalized_face_size[0]}x"
            f"{settings.character.normalized_face_size[1]}px"
        )
        cv2.putText(
            canvas,
            footer_text,
            (self._dims.padding * 3, footer_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (120, 130, 140),
            1,
            cv2.LINE_AA,
        )

        legend_y = footer_y + 30
        legend_items = [
            ('Automatic: Face found on all references', (50, 120, 200)),
            ('Manual: User-selected reference', (180, 100, 50)),
        ]
        for idx, (text, color) in enumerate(legend_items):
            x_pos = self._dims.padding * 3 + idx * 380
            cv2.circle(canvas, (x_pos, legend_y - 3), 5, color, -1)
            cv2.putText(
                canvas,
                text,
                (x_pos + 15, legend_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.38,
                (100, 110, 120),
                1,
                cv2.LINE_AA,
            )

        return canvas

    @staticmethod
    def __load_all_metadata(processed_chars: List[Path]) -> List[Dict[str, Any]]:
        metadata_all = []
        for char_dir in processed_chars:
            metadata_file = char_dir / 'metadata.json'
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata_all.append(json.load(f))
        return metadata_all

    @staticmethod
    def __calculate_avg_similarity(metadata_all: List[Dict[str, Any]]) -> float:
        if not metadata_all:
            return 0.0
        return float(np.mean([m.get('average_similarity', 0) for m in metadata_all]))

    @staticmethod
    def _safe_resize(img: np.ndarray, target_size: Tuple[int, int]) -> Optional[np.ndarray]:
        if img is None or img.size == 0:
            return None
        if img.shape[0] == 0 or img.shape[1] == 0:
            return None
        try:
            return cv2.resize(img, target_size)
        except cv2.error:
            return None

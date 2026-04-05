import asyncio
import json
import logging
import os
from pathlib import Path
import subprocess
import tempfile
from typing import (
    List,
    Optional,
    Tuple,
)

from bot.utils.log import log_system_message
from bot.video.utils import FFMpegException


class TikTakProcessor:
    _ASPECT_9_16 = 9.0 / 16.0
    _MAX_PAN_SPEED = 120.0
    _PERSON_CLASS = "person"
    _CODEC = "libx264"
    _PRESET = "fast"
    _CRF = "23"
    _PROFILE = "high"
    _LEVEL = "4.1"
    _PIX_FMT = "yuv420p"

    @staticmethod
    async def process_single(
        video_path: str,
        start_time: float,
        end_time: float,
        season: int,
        episode_number: int,
        series_name: str,
        detection_dir: str,
        logger: logging.Logger,
    ) -> Path:
        width, height, fps = TikTakProcessor._probe_video(video_path)
        crop_w = TikTakProcessor._even(int(round(height * TikTakProcessor._ASPECT_9_16)))
        max_crop_x = width - crop_w
        center_x = max_crop_x // 2
        duration = end_time - start_time

        raw_points = TikTakProcessor._load_person_bboxes(
            series_name, season, episode_number,
            start_time, end_time, fps, width, crop_w, detection_dir,
        )
        keypoints = TikTakProcessor._build_trajectory(
            raw_points, duration, float(center_x),
        )
        x_expr = TikTakProcessor._piecewise_linear_expr(keypoints, max_crop_x)

        await log_system_message(
            logging.INFO,
            f"TikTak: {len(raw_points)} detection keypoints, crop {crop_w}x{height} from {width}x{height}",
            logger,
        )
        return await TikTakProcessor._run_ffmpeg(
            video_path, start_time, duration, crop_w, height, x_expr,
        )

    @staticmethod
    async def process_compiled(
        video_data: bytes,
        logger: logging.Logger,
    ) -> Path:
        fd, tmp_input = tempfile.mkstemp(suffix=".mp4")
        try:
            os.close(fd)
            Path(tmp_input).write_bytes(video_data)
            width, height, _ = TikTakProcessor._probe_video(tmp_input)
            crop_w = TikTakProcessor._even(int(round(height * TikTakProcessor._ASPECT_9_16)))
            center_x = (width - crop_w) // 2
            duration = TikTakProcessor._probe_duration(tmp_input)
            await log_system_message(
                logging.INFO,
                f"TikTak compiled: center crop {crop_w}x{height} from {width}x{height}",
                logger,
            )
            return await TikTakProcessor._run_ffmpeg(
                tmp_input, 0.0, duration, crop_w, height, str(center_x),
            )
        finally:
            if os.path.exists(tmp_input):
                os.remove(tmp_input)

    @staticmethod
    def _probe_video(video_path: str) -> Tuple[int, int, float]:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,r_frame_rate",
                "-of", "json", str(video_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        stream = data["streams"][0]
        width = int(stream["width"])
        height = int(stream["height"])
        num, den = stream["r_frame_rate"].split("/")
        fps = float(num) / float(den)
        return width, height, fps

    @staticmethod
    def _probe_duration(video_path: str) -> float:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        return float(result.stdout.strip())

    @staticmethod
    def _even(value: int) -> int:
        return value - (value % 2)

    @staticmethod
    def _detection_file_path(
        series_name: str,
        season: int,
        episode_number: int,
        detection_dir: str,
    ) -> Optional[Path]:
        if not detection_dir:
            return None
        ep_code = f"s{season:02d}e{episode_number:02d}"
        filename = f"{series_name.lower()}_{ep_code}_object_detections.json"
        return (
            Path(detection_dir)
            / f"S{season:02d}"
            / f"E{episode_number:02d}"
            / filename
        )

    @staticmethod
    def _extract_frame_point(
        frame_data: dict,
        fps: float,
        start_time: float,
        end_time: float,
        video_width: int,
        crop_width: int,
    ) -> Optional[Tuple[float, float]]:
        frame_num = TikTakProcessor._parse_frame_number(frame_data.get("frame_name", ""))
        if frame_num is None:
            return None
        timestamp = frame_num / fps
        if not start_time - 0.5 <= timestamp <= end_time + 0.5:
            return None
        person_bboxes = [
            d["bbox"]
            for d in frame_data.get("detections", [])
            if d.get("class_name") == TikTakProcessor._PERSON_CLASS
        ]
        if not person_bboxes:
            return None
        return timestamp - start_time, TikTakProcessor._optimal_crop_x(person_bboxes, video_width, crop_width)

    @staticmethod
    def _load_person_bboxes(
        series_name: str,
        season: int,
        episode_number: int,
        start_time: float,
        end_time: float,
        fps: float,
        video_width: int,
        crop_width: int,
        detection_dir: str,
    ) -> List[Tuple[float, float]]:
        det_path = TikTakProcessor._detection_file_path(series_name, season, episode_number, detection_dir)
        if not det_path or not det_path.exists():
            return []
        with open(det_path, encoding="utf-8") as f:
            data = json.load(f)
        points = [
            pt
            for frame_data in data.get("detections", [])
            if (
                pt := TikTakProcessor._extract_frame_point(
                    frame_data, fps, start_time, end_time, video_width, crop_width,
                )
            ) is not None
        ]
        return sorted(points, key=lambda p: p[0])

    @staticmethod
    def _parse_frame_number(frame_name: str) -> Optional[int]:
        try:
            stem = Path(frame_name).stem
            return int(stem.rsplit("_frame_", 1)[1])
        except (IndexError, ValueError):
            return None

    @staticmethod
    def _optimal_crop_x(bboxes: List[dict], video_width: int, crop_width: int) -> float:
        max_crop_x = float(video_width - crop_width)
        if max_crop_x <= 0:
            return 0.0

        candidates = {0.0, max_crop_x}
        for bbox in bboxes:
            candidates.add(max(0.0, min(max_crop_x, bbox["x1"])))
            candidates.add(max(0.0, min(max_crop_x, bbox["x2"] - crop_width)))

        best_x = max_crop_x / 2.0
        best_score = -1.0
        for cx in candidates:
            score = sum(
                max(0.0, min(b["x2"], cx + crop_width) - max(b["x1"], cx))
                * (b["y2"] - b["y1"])
                for b in bboxes
            )
            if score > best_score:
                best_score = score
                best_x = cx

        return best_x

    @staticmethod
    def _build_trajectory(
        raw_points: List[Tuple[float, float]],
        clip_duration: float,
        center_x: float,
    ) -> List[Tuple[float, float]]:
        if not raw_points:
            return [(0.0, center_x), (clip_duration, center_x)]

        points = list(raw_points)
        if points[0][0] > 0.0:
            points.insert(0, (0.0, points[0][1]))
        if points[-1][0] < clip_duration:
            points.append((clip_duration, points[-1][1]))

        return TikTakProcessor._limit_pan_speed(points)

    @staticmethod
    def _limit_pan_speed(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        if len(points) < 2:
            return points
        result = [points[0]]
        for i in range(1, len(points)):
            prev_t, prev_x = result[-1]
            curr_t, curr_x = points[i]
            dt = curr_t - prev_t
            if dt <= 0:
                result.append((curr_t, prev_x))
                continue
            max_dx = TikTakProcessor._MAX_PAN_SPEED * dt
            dx = curr_x - prev_x
            if abs(dx) > max_dx:
                curr_x = prev_x + max_dx * (1.0 if dx > 0 else -1.0)
            result.append((curr_t, curr_x))
        return result

    @staticmethod
    def _piecewise_linear_expr(keypoints: List[Tuple[float, float]], max_crop_x: int) -> str:
        if len(keypoints) == 1:
            return str(int(round(keypoints[0][1])))

        expr = str(int(round(keypoints[-1][1])))
        for i in range(len(keypoints) - 2, -1, -1):
            t0, x0 = keypoints[i]
            t1, x1 = keypoints[i + 1]
            dt = t1 - t0
            if dt <= 0:
                continue
            lerp = f"({x0:.2f}+({x1:.2f}-{x0:.2f})*(t-{t0:.4f})/{dt:.4f})"
            expr = f"if(lt(t,{t1:.4f}),{lerp},{expr})"
        return f"max(0,min({max_crop_x},{expr}))"

    @staticmethod
    async def _run_ffmpeg(
        video_path: str,
        start_time: float,
        duration: float,
        crop_w: int,
        height: int,
        x_expr: str,
    ) -> Path:
        fd, tmp_path = tempfile.mkstemp(suffix=".mp4")
        os.close(fd)
        output = Path(tmp_path)

        filter_str = f"crop={crop_w}:{height}:'{x_expr}':0"
        command = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-i", str(video_path),
            "-t", str(duration),
            "-vf", filter_str,
            "-c:v", TikTakProcessor._CODEC,
            "-preset", TikTakProcessor._PRESET,
            "-crf", TikTakProcessor._CRF,
            "-profile:v", TikTakProcessor._PROFILE,
            "-level", TikTakProcessor._LEVEL,
            "-pix_fmt", TikTakProcessor._PIX_FMT,
            "-c:a", "copy",
            "-movflags", "+faststart",
            "-loglevel", "error",
            str(output),
        ]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise FFMpegException(f"TikTak encoding failed: {stderr.decode()[:300]}")
        return output

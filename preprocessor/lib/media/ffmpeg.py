import json
from pathlib import Path
import subprocess
from typing import (
    Any,
    Dict,
    Optional,
)


class FFmpegWrapper:
    _PROFILE = 'main'
    _LEVEL = '4.1'
    _PIX_FMT = 'yuv420p'
    _BF = '2'
    _B_ADAPT = '1'
    _TWO_PASS = '1'
    _RC_LOOKAHEAD = '32'
    _AQ_STRENGTH = '15'
    _AUDIO_CHANNELS = '2'

    @staticmethod
    def _build_video_filter(width: int, height: int) -> str:
        return (
            f"scale='iw*sar:ih',scale={width}:{height}:"
            f"force_original_aspect_ratio=decrease,pad={width}:{height}:"
            f"(ow-iw)/2:(oh-ih)/2:black,setsar=1"
        )

    @staticmethod
    def _build_base_command(
        input_path: Path, codec: str, preset: str, target_fps: Optional[float],
    ) -> list[str]:
        command = [
            'ffmpeg', '-v', 'error', '-stats', '-hide_banner', '-y',
            '-i', str(input_path),
            '-c:v', codec,
            '-preset', preset,
            '-profile:v', FFmpegWrapper._PROFILE,
            '-level', FFmpegWrapper._LEVEL,
            '-pix_fmt', FFmpegWrapper._PIX_FMT,
        ]
        if target_fps:
            command.extend(['-r', str(target_fps)])
        return command

    @staticmethod
    def _build_encoding_params(
        video_bitrate: str, minrate: str, maxrate: str, bufsize: str, gop_size: int,
    ) -> list[str]:
        return [
            '-rc', 'vbr_hq',
            '-b:v', video_bitrate,
            '-minrate', minrate,
            '-maxrate', maxrate,
            '-bufsize', bufsize,
            '-bf', FFmpegWrapper._BF,
            '-b_adapt', FFmpegWrapper._B_ADAPT,
            '-2pass', FFmpegWrapper._TWO_PASS,
            '-rc-lookahead', FFmpegWrapper._RC_LOOKAHEAD,
            '-aq-strength', FFmpegWrapper._AQ_STRENGTH,
            '-g', str(gop_size),
            '-spatial-aq', '1',
            '-temporal-aq', '1',
            '-multipass', 'fullres',
        ]

    @staticmethod
    def _build_audio_and_output_params(
        audio_bitrate: str, vf_filter: str, output_path: Path,
    ) -> list[str]:
        return [
            '-c:a', 'aac',
            '-b:a', audio_bitrate,
            '-ac', FFmpegWrapper._AUDIO_CHANNELS,
            '-vf', vf_filter,
            '-movflags', '+faststart',
            '-f', 'mp4',
            str(output_path),
        ]

    @staticmethod
    def transcode(  # pylint: disable=too-many-arguments
        input_path: Path,
        output_path: Path,
        codec: str,
        preset: str,
        resolution: str,
        video_bitrate: str,
        minrate: str,
        maxrate: str,
        bufsize: str,
        audio_bitrate: str,
        gop_size: int,
        target_fps: Optional[float] = None,
    ) -> None:
        width, height = [int(x) for x in resolution.split(':')]
        vf_filter = FFmpegWrapper._build_video_filter(width, height)
        command = FFmpegWrapper._build_base_command(input_path, codec, preset, target_fps)
        command.extend(
            FFmpegWrapper._build_encoding_params(
                video_bitrate, minrate, maxrate, bufsize, gop_size,
            ),
        )
        command.extend(
            FFmpegWrapper._build_audio_and_output_params(
                audio_bitrate, vf_filter, output_path,
            ),
        )
        subprocess.run(command, check=True, capture_output=False)

    @staticmethod
    def probe_video(video_path: Path) -> Dict[str, Any]:
        cmd = ['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(video_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)

    @staticmethod
    def _get_stream_by_type(probe_data: Dict[str, Any], codec_type: str) -> Optional[Dict[str, Any]]:
        streams = [s for s in probe_data.get('streams', []) if s.get('codec_type') == codec_type]
        return streams[0] if streams else None

    @staticmethod
    def get_framerate(probe_data: Dict[str, Any]) -> float:
        stream = FFmpegWrapper._get_stream_by_type(probe_data, 'video')
        if not stream:
            raise ValueError('No video streams found')
        r_frame_rate = stream.get('r_frame_rate')
        if not r_frame_rate:
            raise ValueError('Frame rate not found')
        num, denom = [int(x) for x in r_frame_rate.split('/')]
        return num / denom

    @staticmethod
    def get_video_bitrate(probe_data: Dict[str, Any]) -> Optional[float]:
        stream = FFmpegWrapper._get_stream_by_type(probe_data, 'video')
        if not stream:
            return None
        bit_rate = stream.get('bit_rate')
        if not bit_rate:
            return None
        return round(int(bit_rate) / 1000000, 2)

    @staticmethod
    def get_audio_bitrate(probe_data: Dict[str, Any]) -> Optional[int]:
        stream = FFmpegWrapper._get_stream_by_type(probe_data, 'audio')
        if not stream:
            return None
        bit_rate = stream.get('bit_rate')
        if not bit_rate:
            return None
        return int(int(bit_rate) / 1000)

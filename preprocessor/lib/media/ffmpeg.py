import json
from pathlib import Path
import re
import subprocess
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)


class FFmpegWrapper:
    __AQ_STRENGTH = '15'
    __AUDIO_CHANNELS = '2'
    __BF = '2'
    __B_ADAPT = '1'
    __LEVEL = '4.1'
    __PIX_FMT = 'yuv420p'
    __PROFILE = 'main'
    __RC_LOOKAHEAD = '32'
    __TWO_PASS = '1'

    @staticmethod
    def detect_interlacing(
        video_path: Path,
        analysis_time: Optional[int] = None,
        threshold: float = 0.15,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
        ]

        if analysis_time:
            cmd.extend(['-t', str(analysis_time)])

        cmd.extend([
            '-vf', 'idet',
            '-an',
            '-f', 'null',
            '-',
        ])

        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore',
            check=False,
        )

        if result.returncode != 0:
            return False, None

        stats = FFmpegWrapper.__parse_idet_output(result.stderr)
        if stats is None:
            return False, None

        total_interlaced = stats['tff'] + stats['bff']
        total_frames = total_interlaced + stats['progressive']

        if total_frames == 0:
            return False, None

        ratio = total_interlaced / total_frames
        stats['ratio'] = ratio

        return ratio > threshold, stats

    @staticmethod
    def get_audio_bitrate(probe_data: Dict[str, Any]) -> Optional[int]:
        stream = FFmpegWrapper.__get_stream_by_type(probe_data, 'audio')
        if not stream:
            return None
        bit_rate = stream.get('bit_rate')
        if not bit_rate:
            return None
        return int(int(bit_rate) / 1000)

    @staticmethod
    def get_framerate(probe_data: Dict[str, Any]) -> float:
        stream = FFmpegWrapper.__get_stream_by_type(probe_data, 'video')
        if not stream:
            raise ValueError('No video streams found')
        r_frame_rate = stream.get('r_frame_rate')
        if not r_frame_rate:
            raise ValueError('Frame rate not found')
        num, denom = [int(x) for x in r_frame_rate.split('/')]
        return num / denom

    @staticmethod
    def get_video_bitrate(probe_data: Dict[str, Any]) -> Optional[float]:
        stream = FFmpegWrapper.__get_stream_by_type(probe_data, 'video')
        if not stream:
            return None
        bit_rate = stream.get('bit_rate')
        if not bit_rate:
            return None
        return round(int(bit_rate) / 1000000, 2)

    @staticmethod
    def probe_video(video_path: Path) -> Dict[str, Any]:
        cmd = ['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(video_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)

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
        deinterlace: bool = False,
    ) -> None:
        width, height = [int(x) for x in resolution.split(':')]
        vf_filter = FFmpegWrapper.__build_video_filter(width, height, deinterlace)
        command = FFmpegWrapper.__build_base_command(input_path, codec, preset, target_fps)
        command.extend(
            FFmpegWrapper.__build_encoding_params(
                video_bitrate, minrate, maxrate, bufsize, gop_size,
            ),
        )
        command.extend(
            FFmpegWrapper.__build_audio_and_output_params(
                audio_bitrate, vf_filter, output_path,
            ),
        )
        subprocess.run(command, check=True, capture_output=False)

    @staticmethod
    def __build_audio_and_output_params(
        audio_bitrate: str, vf_filter: str, output_path: Path,
    ) -> List[str]:
        return [
            '-c:a', 'aac',
            '-b:a', audio_bitrate,
            '-ac', FFmpegWrapper.__AUDIO_CHANNELS,
            '-vf', vf_filter,
            '-movflags', '+faststart',
            '-f', 'mp4',
            str(output_path),
        ]

    @staticmethod
    def __build_base_command(
        input_path: Path, codec: str, preset: str, target_fps: Optional[float],
    ) -> List[str]:
        command = [
            'ffmpeg', '-v', 'error', '-stats', '-hide_banner', '-y',
            '-i', str(input_path),
            '-c:v', codec,
            '-preset', preset,
            '-profile:v', FFmpegWrapper.__PROFILE,
            '-level', FFmpegWrapper.__LEVEL,
            '-pix_fmt', FFmpegWrapper.__PIX_FMT,
        ]
        if target_fps:
            command.extend(['-r', str(target_fps)])
        return command

    @staticmethod
    def __build_encoding_params(
        video_bitrate: str, minrate: str, maxrate: str, bufsize: str, gop_size: int,
    ) -> List[str]:
        return [
            '-rc', 'vbr_hq',
            '-b:v', video_bitrate,
            '-minrate', minrate,
            '-maxrate', maxrate,
            '-bufsize', bufsize,
            '-bf', FFmpegWrapper.__BF,
            '-b_adapt', FFmpegWrapper.__B_ADAPT,
            '-2pass', FFmpegWrapper.__TWO_PASS,
            '-rc-lookahead', FFmpegWrapper.__RC_LOOKAHEAD,
            '-aq-strength', FFmpegWrapper.__AQ_STRENGTH,
            '-g', str(gop_size),
            '-spatial-aq', '1',
            '-temporal-aq', '1',
            '-multipass', 'fullres',
        ]

    @staticmethod
    def __build_video_filter(width: int, height: int, deinterlace: bool = False) -> str:
        filters = []

        if deinterlace:
            filters.append('bwdif=mode=0')

        filters.append(
            f"scale='iw*sar:ih',scale={width}:{height}:"
            f"force_original_aspect_ratio=decrease,pad={width}:{height}:"
            f"(ow-iw)/2:(oh-ih)/2:black,setsar=1",
        )

        return ','.join(filters)

    @staticmethod
    def __get_stream_by_type(probe_data: Dict[str, Any], codec_type: str) -> Optional[Dict[str, Any]]:
        streams = [s for s in probe_data.get('streams', []) if s.get('codec_type') == codec_type]
        return streams[0] if streams else None

    @staticmethod
    def __parse_idet_output(stderr: str) -> Optional[Dict[str, int]]:
        matches = re.findall(
            r'Multi frame detection:\s+TFF:\s*(\d+)\s+BFF:\s*(\d+)\s+Progressive:\s*(\d+)',
            stderr,
        )

        if not matches:
            return None

        tff, bff, progressive = matches[-1]

        return {
            'tff': int(tff),
            'bff': int(bff),
            'progressive': int(progressive),
        }

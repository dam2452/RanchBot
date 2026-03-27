# pylint: skip-file
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from elevenlabs.client import ElevenLabs
from elevenlabs.core import ApiError

_ELEVENLABS_MODELS = ('scribe_v1', 'scribe_v2')
_WHISPER_MODEL = 'large-v3-turbo'
_POLLING_INTERVAL = 20
_MAX_ATTEMPTS = 120
_ADDITIONAL_FORMATS: List[Dict[str, Any]] = [
    {'format': 'srt'},
    {
        'format': 'segmented_json',
        'include_speakers': True,
        'include_timestamps': True,
        'segment_on_silence_longer_than_s': 0.5,
        'max_segment_duration_s': 10.0,
        'max_segment_chars': 200,
    },
]

_WHISPER_DOCKER_SCRIPT = """
import json, sys
from pathlib import Path
from faster_whisper import WhisperModel

audio_path = sys.argv[1]
out_path = sys.argv[2]
model_name = sys.argv[3]

print(f'[whisper] Loading {model_name} on cuda...')
model = WhisperModel(
    model_name,
    device='cuda',
    compute_type='float16',
    download_root='/models/huggingface',
)

print(f'[whisper] Transcribing {Path(audio_path).name}...')
segments_iter, info = model.transcribe(
    audio_path,
    language='pl',
    beam_size=10,
    temperature=0.0,
    vad_filter=True,
)

segments = []
text_parts = []
for seg in segments_iter:
    text = seg.text.strip()
    text_parts.append(text)
    segments.append({
        'text': text,
        'start': round(seg.start, 3),
        'end': round(seg.end, 3),
        'words': [
            {'text': w.word, 'start': round(w.start, 3), 'end': round(w.end, 3)}
            for w in (seg.words or [])
        ],
    })

result = {'text': ' '.join(text_parts), 'language_code': info.language, 'segments': segments}
Path(out_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'[whisper] Done. {len(segments)} segments saved to {out_path}')
"""


def _extract_audio(video_path: Path, audio_path: Path) -> None:
    print(f'Extracting audio from {video_path.name}...')
    subprocess.run(
        ['ffmpeg', '-y', '-i', str(video_path), '-vn', '-acodec', 'aac', '-b:a', '192k', str(audio_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    print(f'Audio extracted: {audio_path.name} ({audio_path.stat().st_size / 1024 / 1024:.1f} MB)')


def _submit_job(client: ElevenLabs, audio_path: Path, model_id: str, language_code: str, diarize: bool) -> str:
    print(f'[{model_id}] Submitting transcription job...')
    with open(audio_path, 'rb') as f:
        audio_data = f.read()

    response = client.speech_to_text.convert(
        file=audio_data,
        model_id=model_id,
        language_code=language_code,
        tag_audio_events=True,
        timestamps_granularity='character',
        diarize=diarize,
        use_multi_channel=False,
        additional_formats=_ADDITIONAL_FORMATS,
        webhook=True,
    )
    job_id = response.transcription_id
    print(f'[{model_id}] Job submitted. ID: {job_id}')
    return job_id


def _poll_job(client: ElevenLabs, model_id: str, job_id: str) -> Optional[Any]:
    print(f'[{model_id}] Polling for results (ID: {job_id})...')
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            result = client.speech_to_text.transcripts.get(transcription_id=job_id)
            print(f'[{model_id}] Done after {attempt} poll(s).')
            return result
        except ApiError as e:
            if e.status_code == 404:
                print(f'[{model_id}] Not ready yet (attempt {attempt}/{_MAX_ATTEMPTS}), waiting {_POLLING_INTERVAL}s...')
                time.sleep(_POLLING_INTERVAL)
            else:
                raise
    raise TimeoutError(f'[{model_id}] Timeout after {_MAX_ATTEMPTS} attempts')


def _elevenlabs_result_to_dict(result: Any) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        'text': result.text,
        'language_code': result.language_code,
        'segments': [],
        'srt': None,
    }

    if not result.additional_formats:
        return data

    for fmt in result.additional_formats:
        if fmt.requested_format == 'srt':
            data['srt'] = fmt.content
        elif fmt.requested_format == 'segmented_json':
            segmented = json.loads(fmt.content)
            for seg in segmented.get('segments', []):
                words = seg.get('words', [])
                if not words:
                    continue
                non_spacing = [w for w in words if w.get('type') != 'spacing']
                segment: Dict[str, Any] = {'text': seg.get('text', '').strip(), 'words': words}
                if non_spacing:
                    segment['start'] = non_spacing[0].get('start')
                    segment['end'] = non_spacing[-1].get('end')
                    segment['speaker'] = non_spacing[0].get('speaker_id')
                data['segments'].append(segment)

    return data


def _transcribe_whisper_docker(audio_path: Path, json_out: Path) -> None:
    print(f'[whisper_{_WHISPER_MODEL}] Running via Docker (model download may take a moment on first run)...')
    output_dir = audio_path.parent.resolve()

    audio_in_container = f'/compare_output/{audio_path.name}'
    json_in_container = f'/compare_output/{json_out.name}'

    cmd = [
        'docker', 'run', '--rm', '--gpus', 'all',
        '--entrypoint', 'python',
        '-v', f'ranchbot-ai-models:/models',
        '-v', f'{output_dir}:/compare_output',
        'ranczo-preprocessor:latest',
        '-c', _WHISPER_DOCKER_SCRIPT,
        audio_in_container, json_in_container, _WHISPER_MODEL,
    ]

    subprocess.run(cmd, check=True)


def _save_elevenlabs_result(data: Dict[str, Any], output_dir: Path, model_label: str, stem: str) -> Tuple[Path, Optional[Path]]:
    json_path = output_dir / f'{stem}_{model_label}.json'
    srt_content = data.pop('srt', None)
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    srt_path = None
    if srt_content:
        srt_path = output_dir / f'{stem}_{model_label}.srt'
        srt_path.write_text(srt_content, encoding='utf-8')

    return json_path, srt_path


def _json_exists(output_dir: Path, model_label: str, stem: str) -> bool:
    return (output_dir / f'{stem}_{model_label}.json').exists()


def main() -> None:
    parser = argparse.ArgumentParser(description='Compare scribe_v1, scribe_v2 and Whisper transcription quality.')
    parser.add_argument('video', type=Path, help='Path to the video file')
    parser.add_argument('--output-dir', '-o', type=Path, default=None, help='Output directory (default: same as video)')
    parser.add_argument('--language', default='pol', help='ElevenLabs language code (default: pol)')
    parser.add_argument('--no-diarize', action='store_true', help='Disable speaker diarization')
    parser.add_argument('--no-whisper', action='store_true', help='Skip Whisper transcription')
    args = parser.parse_args()

    video_path: Path = args.video.resolve()
    if not video_path.exists():
        raise FileNotFoundError(f'Video file not found: {video_path}')

    output_dir: Path = (args.output_dir or video_path.parent).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = video_path.stem
    diarize = not args.no_diarize
    whisper_label = f'whisper_{_WHISPER_MODEL}'

    elevenlabs_to_run = [m for m in _ELEVENLABS_MODELS if not _json_exists(output_dir, m, stem)]
    whisper_needed = not args.no_whisper and not _json_exists(output_dir, whisper_label, stem)
    need_audio = bool(elevenlabs_to_run) or whisper_needed

    for m in _ELEVENLABS_MODELS:
        if _json_exists(output_dir, m, stem):
            print(f'[{m}] Already exists, skipping API call.')
    if not whisper_needed and not args.no_whisper:
        print(f'[{whisper_label}] Already exists, skipping.')

    job_ids: Dict[str, str] = {}
    audio_temp_dir: Optional[tempfile.TemporaryDirectory] = None  # type: ignore[type-arg]
    audio_path: Optional[Path] = None

    if need_audio:
        audio_temp_dir = tempfile.TemporaryDirectory()
        audio_path = Path(audio_temp_dir.name) / f'{stem}.aac'
        _extract_audio(video_path, audio_path)

    if elevenlabs_to_run:
        api_key = os.getenv('ELEVEN_API_KEY', '')
        if not api_key:
            raise ValueError('ELEVEN_API_KEY environment variable is not set.')
        client = ElevenLabs(api_key=api_key)

        assert audio_path is not None
        for model in elevenlabs_to_run:
            job_ids[model] = _submit_job(client, audio_path, model, args.language, diarize)

        print(f'\n{len(job_ids)} job(s) submitted. Polling for results...\n')
        for model in elevenlabs_to_run:
            result = _poll_job(client, model, job_ids[model])
            data = _elevenlabs_result_to_dict(result)
            json_path, srt_path = _save_elevenlabs_result(data, output_dir, model, stem)
            print(f'[{model}] Saved: {json_path.name} ({len(data["segments"])} segments, {len(data["text"])} chars)')
            if srt_path:
                print(f'[{model}] Saved: {srt_path.name}')

    if whisper_needed:
        assert audio_path is not None
        whisper_audio = output_dir / f'_whisper_tmp_{stem}.aac'
        import shutil
        shutil.copy2(audio_path, whisper_audio)
        try:
            json_out = output_dir / f'{stem}_{whisper_label}.json'
            _transcribe_whisper_docker(whisper_audio, json_out)
            if json_out.exists():
                data = json.loads(json_out.read_text(encoding='utf-8'))
                print(f'[{whisper_label}] Saved: {json_out.name} ({len(data["segments"])} segments, {len(data["text"])} chars)')
        finally:
            whisper_audio.unlink(missing_ok=True)

    if audio_temp_dir:
        audio_temp_dir.cleanup()

    print(f'\nDone. Compare files in: {output_dir}')


if __name__ == '__main__':
    main()

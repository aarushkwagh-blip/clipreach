#!/usr/bin/env python3
"""Local video tools. The host AI agent selects the clips; this script renders them."""
import argparse
import importlib.util
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse


def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, text=True, **kwargs)


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{label} must be a finite number in seconds')
    return float(value)


def read_json(path):
    with Path(path).open(encoding='utf-8') as handle:
        return json.load(handle)


def probe(video):
    video = Path(video).resolve(strict=True)
    result = run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', video], capture_output=True)
    data = json.loads(result.stdout)
    stream = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
    if stream is None:
        raise ValueError('The source has no video stream')
    duration = float(data['format'].get('duration') or stream.get('duration') or 0)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('Cannot determine a positive source duration')
    return {'duration': duration, 'width': stream['width'], 'height': stream['height'],
            'audio': any(s['codec_type'] == 'audio' for s in data['streams'])}


def validate_transcript(data, duration):
    if not isinstance(data, dict) or not isinstance(data.get('segments'), list) or not data['segments']:
        raise ValueError('Transcript needs a nonempty segments array')
    previous = -1
    for segment in data['segments']:
        if not isinstance(segment, dict):
            raise ValueError('Each transcript segment must be an object')
        start = number(segment.get('start'), 'segment.start')
        end = number(segment.get('end'), 'segment.end')
        if not 0 <= start < end <= duration + 0.1 or start < previous:
            raise ValueError('Transcript segments must be ordered and within the source duration')
        previous = start
        if not isinstance(segment.get('text'), str) or not segment['text'].strip():
            raise ValueError('Each segment needs text')
        words = segment.get('words', [])
        if not isinstance(words, list):
            raise ValueError('segment.words must be an array')
        previous_word = start - 0.1
        for word in words:
            if not isinstance(word, dict):
                raise ValueError('Each word must be an object')
            ws = number(word.get('start'), 'word.start')
            we = number(word.get('end'), 'word.end')
            if not start - 0.1 <= ws < we <= end + 0.1 or ws < previous_word:
                raise ValueError('Word timing must be ordered and inside its segment')
            previous_word = we
            if not isinstance(word.get('word'), str) or not word['word'].strip():
                raise ValueError('Each word needs a word string')
    return data['segments']


def validate_plan(data, duration):
    if not isinstance(data, dict) or not isinstance(data.get('clips'), list) or not data['clips']:
        raise ValueError('Plan needs a nonempty clips array')
    for index, clip in enumerate(data['clips'], 1):
        if not isinstance(clip, dict):
            raise ValueError(f'Clip {index} must be an object')
        start = number(clip.get('start'), f'clip {index} start')
        end = number(clip.get('end'), f'clip {index} end')
        if not 0 <= start < end <= duration:
            raise ValueError(f'Clip {index} must satisfy 0 <= start < end <= {duration:.3f}')
        if not isinstance(clip.get('title'), str) or not clip['title'].strip():
            raise ValueError(f'Clip {index} needs a title')
        focus = number(clip.get('focus_x', 0.5), f'clip {index} focus_x')
        if not 0 <= focus <= 1:
            raise ValueError('focus_x must be between 0 (left) and 1 (right)')
        if clip.get('layout', 'pad') not in ('crop', 'pad'):
            raise ValueError('layout must be crop or pad')
    return data['clips']


def ass_time(seconds):
    ticks = max(0, round(seconds * 100))
    hours, ticks = divmod(ticks, 360000)
    minutes, ticks = divmod(ticks, 6000)
    secs, ticks = divmod(ticks, 100)
    return f'{hours}:{minutes:02}:{secs:02}.{ticks:02}'


def escape_ass(text):
    # Transcript text is data: neutralize ASS override syntax before rendering.
    return text.replace('\\', '＼').replace('{', '｛').replace('}', '｝').replace('\r', ' ').replace('\n', ' ')


def captions(segments, start, end, width, height):
    font = max(12, round(width * 0.061))
    margin = round(height * 0.20)
    header = f'''[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{font},&H0000E8FF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,30,30,{margin},1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    events = []
    for segment in segments:
        if segment['end'] <= start or segment['start'] >= end:
            continue
        words = [w for w in segment.get('words', []) if w['end'] > start and w['start'] < end]
        if not segment.get('words'):
            a, b = max(start, segment['start']) - start, min(end, segment['end']) - start
            events.append((a, b, escape_ass(segment['text'].strip())))
            continue
        group = []
        for word in words:
            if group and (len(group) >= 5 or word['end'] - group[0]['start'] > 2.5 or word['start'] - group[-1]['end'] > 0.5):
                events.append(word_event(group, start, end))
                group = []
            group.append(word)
        if group:
            events.append(word_event(group, start, end))
    for a, b, text in events:
        if round(b * 100) > round(a * 100):
            header += f'Dialogue: 0,{ass_time(a)},{ass_time(b)},Default,,0,0,0,,{text}\n'
    return header


def word_event(words, start, end):
    a = max(start, words[0]['start'])
    b = min(end, words[-1]['end'])
    pieces = []
    cursor = a
    for word in words:
        ws, we = max(a, word['start']), min(b, word['end'])
        gap = max(0, round((ws - cursor) * 100))
        if gap:
            pieces.append(f'{{\\k{gap}}}')
        ticks = max(1, round((we - ws) * 100))
        pieces.append(f'{{\\kf{ticks}}}{escape_ass(word["word"].strip())} ')
        cursor = we
    return a - start, b - start, ''.join(pieces).strip()


def doctor(_args):
    missing = []
    for tool in ('ffmpeg', 'ffprobe'):
        found = shutil.which(tool)
        print(f'{tool}: {found or "MISSING"}')
        if not found:
            missing.append(tool)
    if not missing:
        filters = run(['ffmpeg', '-hide_banner', '-filters'], capture_output=True).stdout
        has_ass = any(line.split()[1:2] == ['ass'] for line in filters.splitlines())
        print(f'FFmpeg ASS captions: {"OK" if has_ass else "MISSING (install FFmpeg with libass)"}')
        encoders = run(['ffmpeg', '-hide_banner', '-encoders'], capture_output=True).stdout
        has_h264 = any(line.split()[1:2] == ['libx264'] for line in encoders.splitlines())
        print(f'H.264 encoder: {"OK" if has_h264 else "MISSING (install FFmpeg with libx264)"}')
        if not has_ass or not has_h264:
            missing.append('FFmpeg with libass and libx264')
    for module in ('faster_whisper', 'yt_dlp'):
        print(f'{module}: {"OK" if importlib.util.find_spec(module) else "not installed (optional)"}')
    return 1 if missing else 0


def download(args):
    parsed = urlparse(args.url)
    if parsed.scheme not in ('https', 'http') or not parsed.hostname:
        raise ValueError('Download requires an http(s) video URL')
    if not importlib.util.find_spec('yt_dlp'):
        raise ValueError('Install yt-dlp in the Python environment running this script')
    destination = Path(args.out).resolve()
    if destination.exists():
        raise ValueError(f'Refusing to overwrite {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.clipreach-download-', dir=destination.parent) as tmp:
        folder = Path(tmp)
        run([sys.executable, '-m', 'yt_dlp', '--ignore-config', '--no-playlist', '--no-overwrites',
             '--max-filesize', '5G', '-f', 'bv*[height<=1080]+ba/b[height<=1080]',
             '--merge-output-format', 'mp4', '--remux-video', 'mp4',
             '-o', folder / 'source.%(ext)s', '--', args.url])
        source = folder / 'source.mp4'
        if not source.exists():
            raise ValueError('Downloader did not produce source.mp4')
        probe(source)
        destination.mkdir()
        shutil.move(str(source), destination / 'source.mp4')
    print(destination / 'source.mp4')


def transcribe(args):
    info = probe(args.video)
    if not info['audio']:
        raise ValueError('Source has no audio; use a visual workflow instead of speech transcription')
    destination = Path(args.out).resolve()
    text_path = destination.with_suffix('.txt')
    if destination.suffix.lower() != '.json':
        raise ValueError('Transcript output must end in .json')
    if destination.exists() or text_path.exists():
        raise ValueError('Transcript output already exists; choose a new path')
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise ValueError("Install faster-whisper and 'av<19' in the Python environment running this script") from exc
    model = WhisperModel(args.model, device='cpu', compute_type='int8')
    segments, detected = model.transcribe(str(Path(args.video).resolve()), word_timestamps=True,
                                          vad_filter=True, language=args.language)
    output = {'language': detected.language, 'duration': info['duration'], 'segments': []}
    for segment in segments:
        words = [{'start': w.start, 'end': w.end, 'word': w.word.strip()} for w in segment.words or []
                 if w.end > w.start and w.word.strip()]
        if segment.end > segment.start and segment.text.strip():
            output['segments'].append({'start': segment.start, 'end': segment.end,
                                       'text': segment.text.strip(), 'words': words})
    validate_transcript(output, info['duration'])
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('x', encoding='utf-8') as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2)
    with text_path.open('x', encoding='utf-8') as handle:
        for segment in output['segments']:
            handle.write(f'[{segment["start"]:.2f}–{segment["end"]:.2f}] {segment["text"]}\n')
    print(destination)
    print(text_path)


def render(args):
    video = Path(args.video).resolve(strict=True)
    info = probe(video)
    segments = validate_transcript(read_json(args.transcript), info['duration'])
    clips = validate_plan(read_json(args.plan), info['duration'])
    destination = Path(args.out).resolve()
    if destination.exists():
        raise ValueError(f'Output already exists: {destination}. Choose a new directory.')
    if args.width < 180 or args.width > 2160 or args.width % 18:
        raise ValueError('Width must be a multiple of 18 between 180 and 2160 (e.g. 360, 720, 1080)')
    width, height = args.width, args.width * 16 // 9
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.clipreach-render-', dir=destination.parent) as tmp:
        folder = Path(tmp)
        rendered = []
        for index, clip in enumerate(clips, 1):
            stem = f'clip-{index:03}'
            (folder / f'{stem}.ass').write_text(captions(segments, clip['start'], clip['end'], width, height), encoding='utf-8')
            focus = clip.get('focus_x', 0.5)
            if clip.get('layout', 'pad') == 'crop':
                filters = (f'scale={width}:{height}:force_original_aspect_ratio=increase,'
                           f'crop={width}:{height}:(iw-ow)*{focus}:(ih-oh)/2')
            else:
                filters = (f'scale={width}:{height}:force_original_aspect_ratio=decrease,'
                           f'pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black')
            filters += f',setsar=1,ass={stem}.ass'
            run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-n',
                 '-ss', clip['start'], '-i', video, '-t', clip['end'] - clip['start'],
                 '-map', '0:v:0', '-map', '0:a:0?', '-vf', filters,
                 '-c:v', 'libx264', '-preset', 'fast', '-crf', '20', '-pix_fmt', 'yuv420p',
                 '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', f'{stem}.mp4'], cwd=folder)
            actual = probe(folder / f'{stem}.mp4')
            if actual['width'] != width or actual['height'] != height or abs(actual['duration'] - (clip['end'] - clip['start'])) > 0.5:
                raise ValueError(f'Output verification failed for {stem}')
            rendered.append({**clip, 'file': f'{stem}.mp4', 'captions': f'{stem}.ass',
                             'width': width, 'height': height, 'duration': actual['duration']})
        (folder / 'clips.json').write_text(json.dumps({'clips': rendered}, ensure_ascii=False, indent=2), encoding='utf-8')
        destination.mkdir()
        # Move known artifacts: macOS can relocate AppleDouble sidecars automatically.
        artifacts = [name for clip in rendered for name in (clip['file'], clip['captions'])] + ['clips.json']
        for name in artifacts:
            shutil.move(str(folder / name), destination / name)
    print(f'Rendered {len(clips)} clips to {destination}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('doctor', help='Check local tools; no installation or network requests').set_defaults(func=doctor)
    p = commands.add_parser('inspect', help='Inspect a local source video')
    p.add_argument('video')
    p.set_defaults(func=lambda a: print(json.dumps(probe(a.video), indent=2)))
    p = commands.add_parser('download', help='Download one authorized video; requires yt-dlp')
    p.add_argument('url')
    p.add_argument('--out', required=True, help='New destination directory')
    p.set_defaults(func=download)
    p = commands.add_parser('transcribe', help='Local CPU transcription; requires faster-whisper')
    p.add_argument('video')
    p.add_argument('--out', required=True, help='New transcript.json path')
    p.add_argument('--model', default='small', help='Whisper model name or local model directory')
    p.add_argument('--language', help='Language code; omit for automatic detection')
    p.set_defaults(func=transcribe)
    p = commands.add_parser('render', help='Render agent-selected clips with captions')
    p.add_argument('video')
    p.add_argument('--transcript', required=True)
    p.add_argument('--plan', required=True)
    p.add_argument('--out', required=True, help='New output directory; existing data is never overwritten')
    p.add_argument('--width', type=int, default=1080)
    p.set_defaults(func=render)
    args = parser.parse_args()
    try:
        return args.func(args) or 0
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

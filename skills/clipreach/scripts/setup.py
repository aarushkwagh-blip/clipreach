#!/usr/bin/env python3
"""Check or install ClipReach's isolated Python runtime. Never installs system packages."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]


def runtime_python(runtime):
    return Path(runtime) / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true', help='Create an isolated venv and install optional packages from PyPI')
    parser.add_argument('--runtime', type=Path, default=Path.home() / '.local/share/clipreach/venv')
    args = parser.parse_args()
    runtime = args.runtime.expanduser().resolve()
    python = runtime_python(runtime)
    missing = [tool for tool in ('ffmpeg', 'ffprobe') if not shutil.which(tool)]
    if missing:
        print('Missing: ' + ', '.join(missing), file=sys.stderr)
        print('Install FFmpeg with libass/libx264 using your system package manager (macOS: brew install ffmpeg; Ubuntu: sudo apt-get install ffmpeg).', file=sys.stderr)
        return 1
    try:
        if args.install:
            if sys.version_info < (3, 10):
                raise ValueError('Use Python 3.10 or newer')
            if runtime.exists() and not (runtime / 'pyvenv.cfg').is_file():
                raise ValueError(f'Refusing to modify a non-venv directory: {runtime}')
            if not python.exists():
                venv.EnvBuilder(with_pip=True).create(runtime)
            subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(SKILL / 'requirements.txt')], check=True, stdout=sys.stderr)
        if not python.is_file():
            raise ValueError(f'Runtime not installed. Run this helper with --install --runtime "{runtime}" after approving dependency installation.')
        subprocess.run([str(python), '-c', 'import faster_whisper, yt_dlp; from importlib.metadata import version; assert int(version("av").split(".")[0]) < 19, "Install av<19"'], check=True)
        result = subprocess.run([str(python), str(SKILL / 'scripts/clipreach.py'), 'doctor'], check=True, capture_output=True, text=True)
        print(result.stdout, file=sys.stderr, end='')
        print(json.dumps({'python': str(python), 'script': str(SKILL / 'scripts/clipreach.py'), 'ready': True}, indent=2))
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

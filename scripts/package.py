#!/usr/bin/env python3
"""Build clean skill and plugin archives from the same source."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def clean_files(folder):
    return sorted(p for p in folder.rglob('*') if p.is_file() and not p.is_symlink()
                  and '__pycache__' not in p.parts and not p.name.startswith('._'))


def build(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    skill = ROOT / 'skills/clipreach'
    for kind in ('skill', 'plugin'):
        path = out / ('clipreach.zip' if kind == 'skill' else 'clipreach-plugin.zip')
        files = [(p, Path('clipreach') / p.relative_to(skill)) for p in clean_files(skill)]
        if kind == 'plugin':
            files = [(p, Path('clipreach') / p.relative_to(ROOT)) for p in clean_files(ROOT / 'skills')]
            for name in ['plugin.json', '.codex-plugin/plugin.json', '.claude-plugin/plugin.json',
                         'gemini-extension.json', 'install.py', 'README.md', 'INSTALL.md']:
                files.append((ROOT / name, Path('clipreach') / name))
        for name in (['LICENSE'] if kind == 'skill' else ['LICENSE', 'requirements.txt']):
            files.append((ROOT / name, Path('clipreach') / name))
        with ZipFile(path, 'w', ZIP_DEFLATED) as archive:
            for source, target in files:
                if source.is_symlink():
                    raise ValueError(f'Refusing symlink: {source}')
                archive.write(source, str(target).replace('\\', '/'))
        with ZipFile(path) as archive:
            if archive.testzip():
                raise ValueError(f'Invalid archive: {path}')
        print(path)


if __name__ == '__main__':
    build(ROOT / 'dist')

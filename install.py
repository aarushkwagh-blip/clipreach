#!/usr/bin/env python3
"""Install the ClipReach skill without changing agent settings or overwriting skills."""
import argparse
import shutil
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / 'skills' / 'clipreach'
USER_PATHS = {'codex': '.agents/skills', 'claude-code': '.claude/skills',
              'gemini': '.gemini/skills', 'opencode': '.config/opencode/skills',
              'antigravity': '.gemini/config/skills', 'generic': '.agents/skills'}
PROJECT_PATHS = {**USER_PATHS, 'opencode': '.opencode/skills', 'antigravity': '.agents/skills'}


def source_files():
    return [p for p in SOURCE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.startswith('._')]


def install(destination, dry_run=False):
    destination = Path(destination)
    if destination.is_symlink():
        raise ValueError(f'Refusing an existing symlink: {destination}')
    if destination.exists():
        if not destination.is_dir():
            raise ValueError(f'Destination is not a directory: {destination}')
        expected = {p.relative_to(SOURCE): p.read_bytes() for p in source_files()}
        actual = {p.relative_to(destination): p.read_bytes() for p in destination.rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts and not p.name.startswith('._')}
        if expected != actual:
            raise ValueError(f'{destination} already contains a different skill. Rename or back it up before reinstalling.')
        print(f'Already installed: {destination}')
        return
    print(f'{"Would install" if dry_run else "Installing"}: {destination}')
    if not dry_run:
        shutil.copytree(SOURCE, destination, ignore=shutil.ignore_patterns('__pycache__', '._*'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent', choices=[*USER_PATHS, 'all'], required=True)
    parser.add_argument('--scope', choices=['user', 'project'], default='user')
    parser.add_argument('--home', type=Path, default=Path.home(), help='Home directory for user-scope installation')
    parser.add_argument('--project', type=Path, default=Path.cwd(), help='Project root for project-scope installation')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if not (SOURCE / 'SKILL.md').is_file():
        parser.error('Run this installer from a full ClipReach checkout or plugin archive')
    mapping = USER_PATHS if args.scope == 'user' else PROJECT_PATHS
    base = (args.home if args.scope == 'user' else args.project).expanduser().resolve()
    agents = list(mapping) if args.agent == 'all' else [args.agent]
    try:
        for relative in dict.fromkeys(mapping[agent] for agent in agents):
            install(base / relative / 'clipreach', args.dry_run)
    except (ValueError, OSError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    print('Reload your agent, then ask: Use ClipReach to clip this video: <URL or local file>.')
    print('First use: the skill runs its setup helper; local processing tools are still required.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys


def parse_version(version_str):
    try:
        return tuple(int(x) for x in version_str.strip().split('.'))
    except (ValueError, AttributeError):
        return None


def get_current_version():
    version_file = Path('VERSION')
    if not version_file.exists():
        return None
    return parse_version(version_file.read_text(encoding='utf-8'))


def get_git_hash(ref):
    try:
        return subprocess.run(
            ['git', 'rev-parse', ref],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        return None


def get_target_version():
    head      = get_git_hash('HEAD')
    main_hash = get_git_hash('origin/main')

    ref = 'origin/main~1' if head and head == main_hash else 'origin/main'

    try:
        result = subprocess.run(
            ['git', 'show', f'{ref}:VERSION'],
            capture_output=True,
            text=True,
            check=True,
        )
        return parse_version(result.stdout)
    except subprocess.CalledProcessError:
        return None


def main():
    current_version = get_current_version()
    target_version = get_target_version()

    if current_version is None:
        print('❌ ERROR: Cannot parse current VERSION file')
        sys.exit(1)

    if target_version is None:
        sys.exit(0)

    if current_version <= target_version:
        print('❌ ERROR: Version must be bumped!')
        print(f'   Current version: {".".join(str(x) for x in current_version)}')
        print(f'   Target version:  {".".join(str(x) for x in target_version)}')
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()

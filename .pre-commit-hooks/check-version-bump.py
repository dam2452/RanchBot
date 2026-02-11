#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path


def parse_version(version_str):
    try:
        return tuple(map(int, version_str.strip().split('.')))
    except (ValueError, AttributeError):
        return None


def get_current_version():
    version_file = Path('VERSION')
    if not version_file.exists():
        return None
    return parse_version(version_file.read_text())


def get_main_version():
    try:
        result = subprocess.run(
            ['git', 'show', 'origin/main:VERSION'],
            capture_output=True,
            text=True,
            check=True,
        )
        return parse_version(result.stdout)
    except subprocess.CalledProcessError:
        return None


def main():
    current_version = get_current_version()
    main_version = get_main_version()

    if current_version is None:
        print('❌ ERROR: Cannot parse current VERSION file')
        sys.exit(1)

    if main_version is None:
        sys.exit(0)

    if current_version <= main_version:
        print(f'❌ ERROR: Version must be bumped!')
        print(f'   Current version: {".".join(map(str, current_version))}')
        print(f'   Main version:    {".".join(map(str, main_version))}')
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()

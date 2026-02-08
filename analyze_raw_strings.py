#!/usr/bin/env python3
import ast
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Wzorce do wykluczenia
EXCLUDE_PATTERNS = [
    r"DatabaseKeys\.",
    r"SegmentKeys\.",
    r"EpisodeMetadataKeys\.",
    r"constants\.py",
    r"__pycache__",
    r"test/",
    r"tests/",
]

# Katalogi do analizy
SEARCH_DIRS = ["bot", "preprocessor"]

# Kategoryzacja stringów
raw_strings_data: Dict[str, List[Tuple[str, int]]] = defaultdict(list)


def should_exclude(file_path: str, line: str) -> bool:
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, file_path) or re.search(pattern, line):
            return True
    return False


def extract_get_calls(file_path: Path) -> List[Tuple[str, int, str]]:
    results = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for i, line in enumerate(lines, 1):
                if should_exclude(str(file_path), line):
                    continue

                # .get("key")
                matches = re.findall(r'\.get\s*\(\s*["\']([^"\']+)["\']', line)
                for match in matches:
                    results.append((match, i, line.strip()))

                # ["key"]
                matches = re.findall(r'\[["\']([a-zA-Z_][a-zA-Z0-9_]*)["\'\]]', line)
                for match in matches:
                    results.append((match, i, line.strip()))

                # "key": value w dictach
                matches = re.findall(r'["\']([a-zA-Z_][a-zA-Z0-9_]*)["\'\]]\s*:', line)
                for match in matches:
                    results.append((match, i, line.strip()))

    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    return results


def analyze_directory(base_path: Path, search_dir: str) -> None:
    target_dir = base_path / search_dir
    if not target_dir.exists():
        return

    for py_file in target_dir.rglob("*.py"):
        if any(exclude in str(py_file) for exclude in ["__pycache__", "constants.py"]):
            continue

        strings = extract_get_calls(py_file)
        for string, line_num, line_content in strings:
            raw_strings_data[string].append((str(py_file), line_num))


def main():
    base_path = Path("/mnt/c/GIT_REPO/RANCZO_KLIPY")

    for search_dir in SEARCH_DIRS:
        analyze_directory(base_path, search_dir)

    # Sortuj według liczby wystąpień
    sorted_strings = sorted(raw_strings_data.items(), key=lambda x: len(x[1]), reverse=True)

    print("=" * 80)
    print("RAPORT ANALIZY RAW STRINGÓW")
    print("=" * 80)
    print()

    # Kategoria A: WYSOKIE RYZYKO (3+ wystąpienia)
    print("=" * 80)
    print("KATEGORIA A - WYSOKIE RYZYKO (MUSZĄ BYĆ STAŁYMI)")
    print("Klucze powtarzające się 3+ razy")
    print("=" * 80)
    print()

    for string, locations in sorted_strings:
        if len(locations) >= 3:
            print(f"String: '{string}'")
            print(f"Liczba wystąpień: {len(locations)}")
            print("Lokalizacje:")
            for path, line_num in locations[:10]:  # Pokazuj max 10 lokalizacji
                print(f"  - {path}:{line_num}")
            if len(locations) > 10:
                print(f"  ... i {len(locations) - 10} więcej")
            print()

    # Kategoria B: ŚREDNIE RYZYKO (2 wystąpienia)
    print("=" * 80)
    print("KATEGORIA B - ŚREDNIE RYZYKO (POWINNY BYĆ STAŁYMI)")
    print("Klucze powtarzające się 2 razy")
    print("=" * 80)
    print()

    for string, locations in sorted_strings:
        if len(locations) == 2:
            print(f"String: '{string}'")
            print(f"Liczba wystąpień: {len(locations)}")
            print("Lokalizacje:")
            for path, line_num in locations:
                print(f"  - {path}:{line_num}")
            print()

    # Statystyki
    print("=" * 80)
    print("STATYSTYKI")
    print("=" * 80)
    print(f"Całkowita liczba unikalnych stringów: {len(raw_strings_data)}")
    print(f"Stringi występujące 3+ razy: {sum(1 for s, locs in sorted_strings if len(locs) >= 3)}")
    print(f"Stringi występujące 2 razy: {sum(1 for s, locs in sorted_strings if len(locs) == 2)}")
    print(f"Stringi występujące 1 raz: {sum(1 for s, locs in sorted_strings if len(locs) == 1)}")


if __name__ == "__main__":
    main()

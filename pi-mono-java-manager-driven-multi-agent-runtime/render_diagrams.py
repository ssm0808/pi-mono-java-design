#!/usr/bin/env python3
"""Regenerate changed or all topic-scoped PlantUML diagrams in parallel."""

from __future__ import annotations

import argparse
import concurrent.futures
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = ROOT.parent


def diagram_sources() -> list[Path]:
    return sorted((ROOT / "diagrams").glob("*/diagram.puml"))


def changed_paths() -> set[Path]:
    commands = [
        ["git", "diff", "--name-only"],
        ["git", "diff", "--cached", "--name-only"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]
    result = set()
    for command in commands:
        completed = subprocess.run(command, cwd=REPOSITORY_ROOT, check=True, text=True, capture_output=True)
        result.update((REPOSITORY_ROOT / line).resolve() for line in completed.stdout.splitlines() if line)
    return result


def select_sources(full: bool) -> list[Path]:
    sources = diagram_sources()
    if full:
        return sources
    changed = changed_paths()
    return [source for source in sources if any(path == source or path.parent == source.parent for path in changed)]


def render(source: Path) -> None:
    subprocess.run(["plantuml", "-tsvg", str(source)], cwd=source.parent, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="regenerate every topic")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sources = select_sources(args.full)
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(sources) or 1)) as executor:
        futures = [executor.submit(render, source) for source in sources]
        for future in futures:
            future.result()
    print(f"Rendered {len(sources)} PlantUML topic(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

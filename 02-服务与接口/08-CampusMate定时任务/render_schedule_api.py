#!/usr/bin/env python3
"""Render the mate-service schedule management operations."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MODELS = (
    ROOT / "接口契约" / "操作" / "01-create-schedule.json",
    ROOT / "接口契约" / "操作" / "02-list-schedules.json",
    ROOT / "接口契约" / "操作" / "03-get-schedule.json",
    ROOT / "接口契约" / "操作" / "04-update-schedule.json",
    ROOT / "接口契约" / "操作" / "05-delete-schedule.json",
)
OUTPUT = ROOT / "schedule-api-review.html"


def renderer_path() -> Path:
    configured = os.environ.get("COMPANY_HTTP_API_DESIGN_SKILL_ROOT")
    candidates = []
    if configured:
        candidates.append(Path(configured) / "scripts" / "render_operation_review.py")
    candidates.append(Path.home() / ".codex" / "skills" / "company-http-api-design" / "scripts"
                      / "render_operation_review.py")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "company-http-api-design renderer not found; set COMPANY_HTTP_API_DESIGN_SKILL_ROOT"
    )


def main() -> None:
    command = [
        "python3",
        str(renderer_path()),
        str(MODELS[0]),
        str(OUTPUT),
        "--standalone",
        "--force",
    ]
    for model in MODELS[1:]:
        command.extend(["--include", str(model)])
    subprocess.run(
        command,
        cwd=ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()

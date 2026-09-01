#!/usr/bin/env python3
"""Render the in-review mate-service General Chat events operation."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MODEL = ROOT / "接口契约" / "操作" / "01-submit-chat-event.json"
OUTPUT = ROOT / "chat-events-v1-review.html"


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
    subprocess.run(
        ["python3", str(renderer_path()), str(MODEL), str(OUTPUT), "--standalone", "--force"],
        cwd=ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()

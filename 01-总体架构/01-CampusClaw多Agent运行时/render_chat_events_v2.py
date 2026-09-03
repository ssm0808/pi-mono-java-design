#!/usr/bin/env python3
"""Render the in-review CampusClaw Session Events v2 contract."""

from pathlib import Path

import render_chat_http_v1 as renderer


ROOT = Path(__file__).resolve().parent
renderer.CONTRACT_ROOT = ROOT / "接口契约-v2"
renderer.COMMON_PATH = renderer.CONTRACT_ROOT / "common.json"
renderer.OPERATIONS_ROOT = renderer.CONTRACT_ROOT / "操作"
renderer.DEFAULT_OUTPUT = ROOT / "chat-events-v2-review.html"


if __name__ == "__main__":
    raise SystemExit(renderer.main())

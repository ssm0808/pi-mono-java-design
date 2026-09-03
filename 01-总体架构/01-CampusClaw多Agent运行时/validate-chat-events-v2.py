#!/usr/bin/env python3
"""Validate the current one-operation Session Events v2 review snapshot."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
COMMON_PATH = ROOT / "接口契约-v2" / "common.json"
MODEL_PATH = ROOT / "接口契约-v2" / "操作" / "01-submit-session-event.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> int:
    try:
        common = json.loads(COMMON_PATH.read_text(encoding="utf-8"))
        model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
        operation = model["operation"]
        review = model["review"]
        require(operation["method"] == "POST", "first v2 operation must be POST")
        require(operation["path"] == "/sessions/{sessionId}/events", "unexpected v2 POST path")
        require("text/event-stream" not in json.dumps(operation, ensure_ascii=False), "v2 POST must not return SSE")
        examples = operation["requestBody"]["examples"]
        event_types = {example["value"]["event"]["type"] for example in examples}
        require(
            event_types == {"user.message", "user.interrupt", "user.tool_confirmation"},
            "v2 POST examples must cover all proposed user event types",
        )
        header_sets = [
            ("common", common["requestHeaderExamples"]),
            ("submitSessionEvent", operation["requestHeaderExamples"]),
        ]
        for owner, modes in header_sets:
            for mode in modes:
                x_hw_id = next(header for header in mode["headers"] if header["name"] == "X-HW-ID")
                require(
                    x_hw_id["value"] == "<USER_CREDENTIAL_ID>",
                    f"{owner} {mode['id']} must use the user credential ID placeholder",
                )
                require(
                    "用户凭据 ID" in x_hw_id["description"]
                    and "不是公司、服务或应用标识" in x_hw_id["description"],
                    f"{owner} {mode['id']} must define X-HW-ID as a user credential ID",
                )
        questions = review["questions"]
        require(len(questions) == 4, "the current review must ask exactly four questions")
        for question in questions:
            selected = [option for option in question["options"] if option.get("selected")]
            require(len(selected) == 1, f'{question["id"]} must have one recommended selection')
        subprocess.run([sys.executable, str(ROOT / "render_chat_events_v2.py"), "--check"], check=True)
    except (KeyError, OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"error: {error}")
        return 2
    print("Session Events v2 review snapshot is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

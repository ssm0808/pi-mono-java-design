#!/usr/bin/env python3
"""Render the current operation and a separate read-only confirmed contract."""

import argparse
from pathlib import Path

import render_chat_http_v1 as renderer


ROOT = Path(__file__).resolve().parent
CURRENT_OUTPUT = ROOT / "chat-events-v2-review.html"
CONFIRMED_OUTPUT = ROOT / "chat-events-v2-confirmed.html"


def build_html(confirmed: bool = False) -> str:
    settings = {
        "CONTRACT_ROOT": ROOT / "接口契约-v2",
        "COMMON_PATH": ROOT / "接口契约-v2" / "common.json",
        "OPERATIONS_ROOT": ROOT / "接口契约-v2" / "操作",
    }
    previous = {key: getattr(renderer, key) for key in settings}
    original_loader = renderer.load_contract
    try:
        for key, value in settings.items():
            setattr(renderer, key, value)
        common, models = original_loader()
        state = common["reviewState"]
        keys = state["confirmedOperations"] if confirmed else [state["currentOperation"]]
        selected = [model for model in models if model["operation"]["operationKey"] in keys]
        renderer.require(len(selected) == len(keys) and bool(keys), "Review operation selection is invalid")
        for model in selected:
            model["api"]["visibility"] = (
                "Internal · 已确认接口 · target-only" if confirmed
                else "Internal · 当前评审：实时订阅 · target-only"
            )
        renderer.load_contract = lambda: (common, selected)
        return renderer.build_html()
    finally:
        renderer.load_contract = original_loader
        for key, value in previous.items():
            setattr(renderer, key, value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        for destination, confirmed in ((CURRENT_OUTPUT, False), (CONFIRMED_OUTPUT, True)):
            content = build_html(confirmed)
            if args.check:
                renderer.require(destination.read_text(encoding="utf-8") == content,
                                 f"Generated HTML is out of date: {destination.name}")
            else:
                renderer.write_output(destination, content)
            print(destination)
    except (OSError, KeyError, ValueError) as error:
        print(f"error: {error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

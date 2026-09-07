#!/usr/bin/env python3
"""Render the current operation and retire superseded whole-operation approval."""

import argparse
from pathlib import Path

import render_chat_http_v1 as renderer
from render_chat_api import build_legacy_page


ROOT = Path(__file__).resolve().parent
CURRENT_OUTPUT = ROOT / "chat-events-v2-review.html"
CONFIRMED_OUTPUT = ROOT / "chat-events-v2-confirmed.html"
SUBMIT_OUTPUT = ROOT / "chat-events-v2-submit-review.html"


def build_html(confirmed: bool = False, operation_key: str | None = None) -> str:
    if confirmed:
        return build_legacy_page(CONFIRMED_OUTPUT.name)
    return build_legacy_page(SUBMIT_OUTPUT.name if operation_key == "submitSessionEvent" else CURRENT_OUTPUT.name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        for destination, confirmed, key in (
            (CURRENT_OUTPUT, False, None), (CONFIRMED_OUTPUT, True, None),
            (SUBMIT_OUTPUT, False, "submitSessionEvent"),
        ):
            content = build_html(confirmed, key)
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

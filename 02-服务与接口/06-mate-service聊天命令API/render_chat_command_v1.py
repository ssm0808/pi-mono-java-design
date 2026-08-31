#!/usr/bin/env python3
"""Render the source-first mate-service Chat Command contract as standalone HTML."""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import tempfile
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = ROOT.parents[1]
RUNTIME_ROOT = REPOSITORY_ROOT / "01-总体架构" / "01-CampusClaw多Agent运行时"
RUNTIME_RENDERER = RUNTIME_ROOT / "render_chat_http_v1.py"
CONTRACT_ROOT = ROOT / "接口契约"
DEFAULT_OUTPUT = ROOT / "chat-command-v1-review.html"


def load_runtime_renderer() -> Any:
    spec = importlib.util.spec_from_file_location("runtime_contract_renderer", RUNTIME_RENDERER)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load the shared Runtime contract renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SHARED = load_runtime_renderer()


def load_contract() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    common = json.loads((CONTRACT_ROOT / "common.json").read_text(encoding="utf-8"))
    SHARED.require(isinstance(common, dict), "common.json must contain a JSON object")
    operation_paths = sorted((CONTRACT_ROOT / "操作").glob("*.json"))
    SHARED.require(operation_paths, "No public command operation models found")
    sources = [json.loads(path.read_text(encoding="utf-8")) for path in operation_paths]
    SHARED.require(all(isinstance(source, dict) for source in sources), "Operation sources must be JSON objects")
    models = [SHARED.expand_model(common, source) for source in sources]
    keys = [model["operation"]["operationKey"] for model in models]
    identities = [f'{model["operation"]["method"]} {model["operation"]["path"]}' for model in models]
    SHARED.require(len(keys) == len(set(keys)), "operationKey values must be unique")
    SHARED.require(len(identities) == len(set(identities)), "HTTP operation identities must be unique")
    return common, models


def build_html() -> str:
    _, models = load_contract()
    css = (RUNTIME_ROOT / "接口契约" / "页面资源" / "review.css").read_text(encoding="utf-8").strip()
    script = (RUNTIME_ROOT / "接口契约" / "页面资源" / "review.js").read_text(encoding="utf-8").strip()
    cards = []
    for index, model in enumerate(models):
        operation_key = model["operation"]["operationKey"]
        cards.append(
            f'<section class="company-api-review" data-operation-review="{html.escape(operation_key, quote=True)}" '
            f'data-operation-index="{index}"><div class="api-shell" data-api-shell aria-live="polite">'
            f'{SHARED.render_static(model)}</div></section>'
        )
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="referrer" content="no-referrer">
  <title>{html.escape(models[0]["api"]["title"])} - API Review</title>
  <style>
{css}
  </style>
</head>
<body>
  <!-- Generated from 接口契约/common.json and 接口契约/操作/*.json. Do not edit this HTML directly. -->
  <main>
{"".join(cards)}
  </main>
  <script type="application/json" id="api-review-models">{SHARED.encode_models(models)}</script>
  <script>
{script}
  </script>
</body>
</html>
'''


def write_output(destination: Path, content: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=destination.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, destination)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    content = build_html()
    destination = args.output.resolve()
    if args.check:
        SHARED.require(destination.exists(), f"Generated HTML is missing: {destination}")
        SHARED.require(destination.read_text(encoding="utf-8") == content, "Generated HTML is out of date")
    else:
        write_output(destination, content)
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

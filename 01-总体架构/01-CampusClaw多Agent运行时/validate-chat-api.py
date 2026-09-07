#!/usr/bin/env python3
"""Single validation entrypoint for the current CampusClaw API catalog."""

import argparse
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import render_chat_api as current

ROOT = Path(__file__).resolve().parent


def require(value, message):
    if not value:
        raise ValueError(message)


def validate_catalog():
    manifest, models = current.load_catalog()
    require(len(models) == 10, "Current catalog must contain exactly ten operations")
    require({model["operation"]["operationKey"] for model in models} == {
        "createSession", "getSession", "deleteSession", "submitSessionEvent", "listSessionEvents",
        "listSessionModels", "changeSessionModel", "changeSessionThinking",
        "listSessionCommands", "executeSessionCommand",
    }, "Current catalog identities differ")
    spec = importlib.util.spec_from_file_location("retained_gate", ROOT / "validate-chat-http-v1.py")
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    source = (ROOT / manifest["output"]).read_text(encoding="utf-8")
    require(source == current.build_html(), "Current HTML is stale")
    parser = gate.ContractHtmlParser()
    parser.feed(source)
    embedded, scripts = gate.parse_generated_models(parser)
    require(embedded == models and parser.static_review_count == 10, "Rendered model/static catalog differs")
    require(len(scripts) == len(parser.styles) == 1, "Keep one shared script and style")
    gate.validate_executable_script(scripts[0])
    gate.validate_control_retirement(models)
    for name in manifest["legacyPages"]:
        legacy = (ROOT / name).read_text(encoding="utf-8")
        require(legacy == current.build_legacy_page(name), f"Stale legacy entry: {name}")
        require("data-operation-review" not in legacy and "application/json" not in legacy,
                f"Legacy page must not contain contract payloads: {name}")
        require("chat-api-review.html" in legacy, f"Legacy entry must link the current catalog: {name}")
    for name in ("04-submit-user-message.json", "05-list-session-events.json"):
        require(not (ROOT / "接口契约/操作" / name).exists(), "Retired Events source reintroduced")
    for item in manifest["operations"]:
        require((ROOT / item["design"].split("#")[0]).exists(), "Missing design reference")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    inventory = readme.split("## 4. 当前目标 HTTP 接口清单", 1)[1].split("## 5.", 1)[0]
    routes = re.findall(r"\| \d+ \| `(GET|POST|PUT|DELETE)` \| `([^`]+)`", inventory)
    expected = [(model["operation"]["method"], model["operation"]["path"]) for model in models]
    require(routes == expected, "README inventory differs from the single catalog")
    for target in re.findall(r'href="([^"#]+)(?:#[^"]*)?"', source):
        require((ROOT / target).exists(), f"Broken current-page link: {target}")
    require("traceparent" not in source, "Forbidden header in current page")
    require(len(source.encode()) < 500_000, "Unexpected catalog growth")
    return models


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    for command in (
        ["render_chat_api.py", "--check"],
        ["validate-chat-http-v1.py", *(["--full"] if args.full else [])],
        ["validate-chat-events-v2.py"],
        ["test_control_retirement.py"],
        ["test_chat_api.py"],
        ["test_help_contract.py"],
    ):
        subprocess.run([sys.executable, *command], cwd=ROOT, check=True)
    validate_catalog()
    print("Current catalog valid: ten unique operations; old entries carry no payload; review decisions preserved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

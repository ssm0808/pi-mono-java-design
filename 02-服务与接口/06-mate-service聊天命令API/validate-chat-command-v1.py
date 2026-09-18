#!/usr/bin/env python3
"""Validate the source-first mate-service Chat Command contract and artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from render_chat_command_v1 import build_html, load_contract, RUNTIME_ROOT

sys.path.insert(0, str(RUNTIME_ROOT))
from command_catalog_contract import validate_catalog_examples, validate_projection_pair


ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = ROOT.parents[1]
HTML_PATH = ROOT / "chat-command-v1-review.html"
DESIGN_PATH = ROOT / "README.md"
LOWER_CAMEL = re.compile(r"^[a-z][A-Za-z0-9]*$")
EXPECTED_OPERATIONS = {
    ("GET", "/chats/{chatId}/commands"),
}


class ReviewHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.static_count = 0
        self.business_count = 0
        self.exact_contract_count = 0
        self.open_exact_contract_count = 0
        self.styles: list[str] = []
        self.scripts: list[tuple[dict[str, str | None], str]] = []
        self.visible: list[str] = []
        self.capture: str | None = None
        self.attributes: dict[str, str | None] = {}
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if "data-static-review" in attributes:
            self.static_count += 1
        if "data-business-review" in attributes:
            self.business_count += 1
        if tag == "details" and "exact-contract" in (attributes.get("class") or "").split():
            self.exact_contract_count += 1
            if "open" in attributes:
                self.open_exact_contract_count += 1
        if tag in {"style", "script"}:
            self.capture = tag
            self.attributes = attributes
            self.parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag != self.capture:
            return
        source = "".join(self.parts)
        if tag == "style":
            self.styles.append(source)
        else:
            self.scripts.append((self.attributes, source))
        self.capture = None
        self.attributes = {}
        self.parts = []

    def handle_data(self, data: str) -> None:
        if self.capture is not None:
            self.parts.append(data)
        elif data.strip():
            self.visible.append(data.strip())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run(command: list[str], cwd: Path = ROOT) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def validate_keys(value: Any, context: str) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            require(LOWER_CAMEL.fullmatch(key) is not None, f"Non-lowerCamel field in {context}: {key}")
            validate_keys(nested, context)
    elif isinstance(value, list):
        for item in value:
            validate_keys(item, context)


def values_for_key(value: Any, key: str):
    if isinstance(value, dict):
        for current, nested in value.items():
            if current == key:
                yield nested
            yield from values_for_key(nested, key)
    elif isinstance(value, list):
        for item in value:
            yield from values_for_key(item, key)


def validate_contract(common: dict[str, Any], models: list[dict[str, Any]]) -> None:
    require(common["api"]["version"] == "1.3.0", "Unexpected public contract version")
    require(common["api"]["basePath"] == "/mate-service/v1", "Unexpected public base path")
    require("GET 字段已确认" in common["api"]["visibility"] and "公共边界待评审" in common["api"]["visibility"],
            "GET confirmation must not approve the public boundary")
    require("commandLimits" not in common and "commandNamePatterns" not in common,
            "Retired POST-only common definitions must not return")
    headers = {
        header["name"]
        for example in common["requestHeaderExamples"]
        for header in example["headers"]
    }
    require(headers == {"Authorization"}, "Public auth must not expose internal Header names")
    operations = {(model["operation"]["method"], model["operation"]["path"]) for model in models}
    require(operations == EXPECTED_OPERATIONS, "Public operation inventory differs")
    require(len(models) == 1, "Expected only the retained public GET projection")
    for model in models:
        operation = model["operation"]
        business_view = model["review"].get("businessView")
        require(isinstance(business_view, dict), "Human review business view is required")
        require(isinstance(business_view.get("summary"), str) and business_view["summary"],
                "Human review summary is required")
        require(isinstance(business_view.get("flow"), list) and business_view["flow"],
                "Human review flow is required")
        require("待实现 design" in operation["description"] and "不得作为实现依据" in operation["description"],
                "Operation must state the pending 待实现 public boundary")
        placeholders = re.findall(r"{([^}]+)}", operation["path"])
        require(all(LOWER_CAMEL.fullmatch(item) for item in placeholders), "Path fields must be lowerCamelCase")
        for response in operation["responses"]:
            for body in response.get("bodies", {}).values():
                if isinstance(body, (dict, list)):
                    validate_keys(body, operation["operationKey"])
    validate_catalog(models)


def validate_catalog(models: list[dict[str, Any]]) -> None:
    operation = next(model["operation"] for model in models if model["operation"]["operationKey"] == "listChatCommands")
    validate_catalog_examples(operation)
    runtime = json.loads((RUNTIME_ROOT / "接口契约/操作/12-list-session-commands.json").read_text(encoding="utf-8"))
    validate_projection_pair(runtime["operation"], operation)
    codes = set(values_for_key(operation["responses"], "resCode"))
    require({"UNAUTHENTICATED", "CHAT_ACCESS_DENIED", "CHAT_NOT_FOUND", "COMMAND_CATALOG_UNAVAILABLE"} <= codes,
            "Catalog public errors are incomplete")


def validate_html(models: list[dict[str, Any]]) -> None:
    source = HTML_PATH.read_text(encoding="utf-8")
    require(source == build_html(), "Generated public review HTML is stale")
    parser = ReviewHtmlParser()
    parser.feed(source)
    require(parser.static_count == 1, "No-script operation count is wrong")
    require(parser.business_count == 1, "Business review operation count is wrong")
    require(parser.exact_contract_count == 1, "Exact contract fold count is wrong")
    require(parser.open_exact_contract_count == 0, "Raw protocol must be folded by default")
    require(len(parser.styles) == 1, "Expected one shared style block")
    model_scripts = [json.loads(script) for attrs, script in parser.scripts
                     if attrs.get("type") == "application/json" and attrs.get("id") == "api-review-models"]
    require(model_scripts == [models], "Embedded review models differ from sources")
    executable = [script for attrs, script in parser.scripts if attrs.get("type") != "application/json"]
    require(len(executable) == 1, "Expected one executable script")
    with tempfile.TemporaryDirectory() as directory:
        script_path = Path(directory) / "review.js"
        script_path.write_text(executable[0], encoding="utf-8")
        run(["node", "--check", str(script_path)])
    visible = " ".join(parser.visible)
    for heading in ("业务评审视图", "前后端怎么交互", "作用", "调用上下文 Header", "参数与请求体", "响应"):
        require(heading in visible, f"No-script review is missing {heading}")
    require("查看 GET HTTP / JSON 报文（公共边界待评审）" in visible,
            "Raw protocol fold is missing")
    require(source.index("data-business-review") < source.index("class=\"exact-contract\""),
            "Business review must appear before the raw protocol")
    require("字段：lowerCamelCase" in visible and "Header：保留原名" in visible,
            "Review does not expose naming rules")
    require(re.search(r"@media\s*\(max-width:\s*680px\)", source) is not None,
            "Mobile breakpoint is missing")
    require("content: attr(data-label)" in source, "Responsive labeled rows are missing")


def validate_retirement(root: Path = ROOT) -> None:
    retired = (
        "接口契约/操作/02-execute-chat-command.json",
        "设计图/diagram.puml",
        "设计图/public_command_boundary.svg",
        "设计图/public_sse_projection.svg",
    )
    for path in retired:
        require(not (root / path).exists(), f"Retired Command artifact returned: {path}")
    sources = {path.name for path in (root / "接口契约/操作").glob("*.json")}
    require(sources == {"01-list-chat-commands.json"}, "Only the retained GET model may remain")


def validate_markdown() -> None:
    content = DESIGN_PATH.read_text(encoding="utf-8")
    require("```mermaid" not in content, "Mermaid is forbidden")
    require("目录" not in content, "Public Command design must use 命令清单 or an explicit file term")
    for target in re.findall(r"!\[[^\]]*\]\(([^)]+\.svg)\)", content):
        require((ROOT / target).exists(), f"Missing SVG link: {target}")
    for target, line_text in re.findall(r"\[[^\]]+\]\(([^)#]+\.puml)#L([0-9]+)\)", content):
        source = (ROOT / target).resolve()
        lines = source.read_text(encoding="ascii").splitlines()
        line = int(line_text)
        require(0 < line <= len(lines) and lines[line - 1].startswith("@startuml"),
                f"Invalid PlantUML source anchor: {target}#L{line}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="reserved for parity with other contract validators")
    parser.parse_args()
    common, models = load_contract()
    validate_contract(common, models)
    require("目录" not in json.dumps(models, ensure_ascii=False),
            "Public Command contract must use 命令清单 or an explicit file term")
    validate_html(models)
    validate_retirement()
    validate_markdown()
    run(["git", "diff", "--check"], REPOSITORY_ROOT)
    print("mate-service Chat Command contract validation passed: 1 GET projection; public boundary pending; retired POST and diagrams absent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

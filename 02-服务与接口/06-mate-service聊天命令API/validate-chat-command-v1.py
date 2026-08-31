#!/usr/bin/env python3
"""Validate the source-first mate-service Chat Command contract and artifacts."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from render_chat_command_v1 import build_html, load_contract


ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = ROOT.parents[1]
HTML_PATH = ROOT / "chat-command-v1-review.html"
DESIGN_PATH = ROOT / "README.md"
LOWER_CAMEL = re.compile(r"^[a-z][A-Za-z0-9]*$")
EXPECTED_OPERATIONS = {
    ("GET", "/chats/{chatId}/commands"),
    ("POST", "/chats/{chatId}/command"),
}


class ReviewHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.static_count = 0
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


def sse_payloads(stream: str) -> list[dict[str, Any]]:
    payloads = []
    for line in stream.splitlines():
        if line.startswith("data: "):
            payload = json.loads(line.removeprefix("data: "))
            require(isinstance(payload, dict), "SSE data must contain a JSON object")
            payloads.append(payload)
    return payloads


def validate_contract(common: dict[str, Any], models: list[dict[str, Any]]) -> None:
    require(common["api"]["version"] == "1.0.2", "Unexpected public contract version")
    require(common["api"]["basePath"] == "/mate-service/v1", "Unexpected public base path")
    require("target-only" in common["api"]["visibility"], "Public contract must remain target-only")
    headers = {
        header["name"]
        for example in common["requestHeaderExamples"]
        for header in example["headers"]
    }
    require(headers == {"Authorization"}, "Public auth must not expose internal Header names")
    operations = {(model["operation"]["method"], model["operation"]["path"]) for model in models}
    require(operations == EXPECTED_OPERATIONS, "Public operation inventory differs")
    require(len(models) == 2, "Expected two public command operations")
    for model in models:
        operation = model["operation"]
        require("target-only design" in operation["description"], "Operation must state target-only status")
        placeholders = re.findall(r"{([^}]+)}", operation["path"])
        require(all(LOWER_CAMEL.fullmatch(item) for item in placeholders), "Path fields must be lowerCamelCase")
        for response in operation["responses"]:
            for body in response.get("bodies", {}).values():
                if isinstance(body, (dict, list)):
                    validate_keys(body, operation["operationKey"])
    validate_catalog(models)
    validate_execution(models)


def validate_catalog(models: list[dict[str, Any]]) -> None:
    operation = next(model["operation"] for model in models if model["operation"]["operationKey"] == "listChatCommands")
    success = next(response for response in operation["responses"] if response["status"] == "200")
    commands = success["bodies"]["zh-CN"]["result"]["commands"]
    names = {command["name"] for command in commands}
    require({"help", "status", "name", "model", "thinking", "compact", "skills", "skill:pdf"} <= names,
            "Catalog example is incomplete")
    model = next(command for command in commands if command["name"] == "model")
    require(model["available"] is True and model["input"]["available"] is False,
            "Catalog must preserve two-level running availability")
    skill = next(command for command in commands if command["name"] == "skill:pdf")
    require(skill["input"]["acceptsFiles"] is True, "Skill must advertise attachment support")
    codes = set(values_for_key(operation["responses"], "resCode"))
    require({"UNAUTHENTICATED", "CHAT_ACCESS_DENIED", "CHAT_NOT_FOUND", "COMMAND_CATALOG_UNAVAILABLE"} <= codes,
            "Catalog public errors are incomplete")


def validate_execution(models: list[dict[str, Any]]) -> None:
    operation = next(model["operation"] for model in models if model["operation"]["operationKey"] == "executeChatCommand")
    require(set(operation["requestBody"]["example"]) == {"name", "arguments", "fileIds"},
            "Command request shape changed")
    codes = set(values_for_key(operation["responses"], "resCode"))
    for code in {"INVALID_COMMAND_REQUEST", "COMMAND_NOT_FOUND", "SESSION_BUSY", "COMMAND_UNAVAILABLE"}:
        require(code in codes, f"Missing public error: {code}")
    streams = [response["bodies"]["default"] for response in operation["responses"]
               if response["status"] == "200" and "default" in response.get("bodies", {})]
    require(any("event: session.name.changed" in stream for stream in streams), "Name event missing")
    require(any("event: assistant.message.completed" in stream for stream in streams), "Skill result missing")
    failed = next(stream for stream in streams if "event: command.failed" in stream)
    require("event: stream.error" in failed and "event: stream.end" not in failed,
            "Failed stream terminal semantics changed")
    for stream in streams:
        for payload in sse_payloads(stream):
            validate_keys(payload, "public SSE")
            for forbidden in ("sessionId", "entryId", "entrySeq", "agentId", "skillId", "skillVersion", "snapshot"):
                require(not any(True for _ in values_for_key(payload, forbidden)),
                        f"Internal field leaked to public SSE: {forbidden}")
    successful_payloads = [payload for stream in streams for payload in sse_payloads(stream)]
    require(any(True for payload in successful_payloads for _ in values_for_key(payload, "sourceEventSeq")),
            "Public completion must retain sourceEventSeq")


def validate_html(models: list[dict[str, Any]]) -> None:
    source = HTML_PATH.read_text(encoding="utf-8")
    require(source == build_html(), "Generated public review HTML is stale")
    parser = ReviewHtmlParser()
    parser.feed(source)
    require(parser.static_count == 2, "No-script operation count is wrong")
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
    for heading in ("作用", "调用上下文 Header", "参数与请求体", "响应"):
        require(heading in visible, f"No-script review is missing {heading}")
    require("字段：lowerCamelCase" in visible and "Header：保留原名" in visible,
            "Review does not expose naming rules")
    require(re.search(r"@media\s*\(max-width:\s*680px\)", source) is not None,
            "Mobile breakpoint is missing")
    require("content: attr(data-label)" in source, "Responsive labeled rows are missing")


def diagram_names(source: Path) -> list[str]:
    content = source.read_text(encoding="ascii")
    names = re.findall(r"^@startuml\s+([A-Za-z0-9_]+)\s*$", content, re.MULTILINE)
    require(names, "PlantUML must contain named diagrams")
    return names


def validate_diagrams() -> None:
    source = ROOT / "设计图" / "diagram.puml"
    require(source.read_bytes().isascii(), "PlantUML must be ASCII-only")
    names = diagram_names(source)
    expected = {f"{name}.svg" for name in names}
    actual = {path.name for path in source.parent.glob("*.svg")}
    require(actual == expected, "Public command SVG inventory differs")
    for svg in source.parent.glob("*.svg"):
        ET.parse(svg)
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory) / "diagram.puml"
        shutil.copy2(source, temporary)
        run(["plantuml", "-tsvg", str(temporary)], Path(directory))
        for name in names:
            require((Path(directory) / f"{name}.svg").read_bytes() == (source.parent / f"{name}.svg").read_bytes(),
                    f"Generated SVG is stale: {name}.svg")


def validate_markdown() -> None:
    content = DESIGN_PATH.read_text(encoding="utf-8")
    require("```mermaid" not in content, "Mermaid is forbidden")
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
    validate_html(models)
    validate_diagrams()
    validate_markdown()
    run(["git", "diff", "--check"], REPOSITORY_ROOT)
    print("mate-service Chat Command contract validation passed: 2 operations, 1 diagram topic")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

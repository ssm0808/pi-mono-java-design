#!/usr/bin/env python3
"""Validate the in-review mate-service General Chat events artifacts."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from render_chat_events_v1 import MODEL, OUTPUT, ROOT, renderer_path


REPOSITORY_ROOT = ROOT.parents[1]
DESIGN = ROOT / "README.md"
PUML = ROOT / "设计图" / "diagram.puml"
LOWER_CAMEL = re.compile(r"^[a-z][A-Za-z0-9]*$")
FORBIDDEN_PUBLIC_FIELDS = {
    "sessionId", "entryId", "entrySeq", "assistantEntryId", "toolCallId",
    "agentId", "skillId", "toolId", "runId", "usage", "cost",
}


class ScriptParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.capture = False
        self.attributes: dict[str, str | None] = {}
        self.parts: list[str] = []
        self.scripts: list[tuple[dict[str, str | None], str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script":
            self.capture = True
            self.attributes = dict(attrs)
            self.parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self.capture:
            self.scripts.append((self.attributes, "".join(self.parts)))
            self.capture = False

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.parts.append(data)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run(command: list[str], cwd: Path = ROOT) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def values_for_key(value: Any, key: str):
    if isinstance(value, dict):
        for current, nested in value.items():
            if current == key:
                yield nested
            yield from values_for_key(nested, key)
    elif isinstance(value, list):
        for item in value:
            yield from values_for_key(item, key)


def validate_lower_camel(value: Any, context: str) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            require(LOWER_CAMEL.fullmatch(key) is not None, f"Non-lowerCamel field in {context}: {key}")
            validate_lower_camel(nested, context)
    elif isinstance(value, list):
        for item in value:
            validate_lower_camel(item, context)


def sse_frames(stream: str) -> list[tuple[str, str | None, dict[str, Any]]]:
    frames = []
    for block in stream.strip().split("\n\n"):
        event = None
        event_id = None
        payload = None
        for line in block.splitlines():
            if line.startswith("event: "):
                event = line.removeprefix("event: ")
            elif line.startswith("id: "):
                event_id = line.removeprefix("id: ")
            elif line.startswith("data: "):
                payload = json.loads(line.removeprefix("data: "))
        require(event is not None and isinstance(payload, dict), f"Malformed SSE frame: {block}")
        frames.append((event, event_id, payload))
    return frames


def validate_model(model: dict[str, Any]) -> None:
    require(model["api"]["version"] == "0.1.0", "Unexpected contract version")
    require(model["api"]["basePath"] == "/mate-service/v1", "Unexpected base path")
    require("评审中" in model["api"]["visibility"], "Operation must remain in review")
    operation = model["operation"]
    require((operation["method"], operation["path"]) ==
            ("POST", "/chats/{chatId}/events"), "Operation path changed")
    request_example = operation["requestBody"]["example"]
    require(set(request_example) == {"message", "fileIds"},
            "Request example must contain only message and fileIds")
    require(all(re.fullmatch(r"file_[0-9A-Za-z]{26}", file_id) for file_id in request_example["fileIds"]),
            "Request example contains an invalid fileId")
    auth_headers = {header["name"] for mode in operation["authModes"] for header in mode["headers"]}
    require(auth_headers == {"Authorization"}, "Recommended public auth exposes internal headers")
    questions = model["review"]["questions"]
    require(len(questions) == 4, "Exactly four unresolved question groups are allowed")
    require(all(sum(bool(option.get("selected")) for option in group["options"]) == 1 for group in questions),
            "Each question must select exactly one recommended option")
    codes = set(values_for_key(operation["responses"], "resCode"))
    for response in operation["responses"]:
        for body in response.get("bodies", {}).values():
            if isinstance(body, str):
                codes.update(payload["resCode"] for _, _, payload in sse_frames(body) if "resCode" in payload)
    required_codes = {
        "INVALID_CHAT_ID", "INVALID_EVENT_REQUEST", "UNAUTHENTICATED", "CHAT_ACCESS_DENIED",
        "CHAT_NOT_FOUND", "CHAT_BUSY", "CHAT_RATE_LIMITED", "RUNTIME_EVENT_FAILED",
        "CHAT_EXECUTION_UNAVAILABLE", "CHAT_EXECUTION_FAILED",
    }
    require(required_codes <= codes, f"Missing public errors: {sorted(required_codes - codes)}")
    success = next(item for item in operation["responses"] if item["id"] == "200-success")
    frames = sse_frames(success["bodies"]["default"])
    names = [frame[0] for frame in frames]
    for expected in ("user.message", "assistant.thinking.completed", "tool.result",
                     "assistant.message.completed", "session.status.idle", "stream.end"):
        require(expected in names, f"Missing SSE event: {expected}")
    require(names[-2:] == ["session.status.idle", "stream.end"], "Normal SSE terminal order changed")
    for _, event_id, payload in frames:
        validate_lower_camel(payload, "public SSE")
        for forbidden in FORBIDDEN_PUBLIC_FIELDS:
            require(not any(True for _ in values_for_key(payload, forbidden)),
                    f"Internal field leaked to public SSE: {forbidden}")
        if event_id is not None:
            require(str(payload.get("eventSeq")) == event_id, "SSE id must equal public eventSeq")
    failure = next(item for item in operation["responses"] if item["id"] == "200-stream-error")
    failed_frames = sse_frames(failure["bodies"]["default"])
    require([item[0] for item in failed_frames] == ["stream.error"],
            "Established failure must contain only stream.error")
    require(failed_frames[0][2].get("accepted") is True, "Established failure must mark accepted=true")


def validate_html() -> None:
    require(OUTPUT.is_file(), "Generated review HTML is missing")
    with tempfile.TemporaryDirectory() as directory:
        candidate = Path(directory) / OUTPUT.name
        run(["python3", str(renderer_path()), str(MODEL), str(candidate), "--standalone"])
        require(candidate.read_bytes() == OUTPUT.read_bytes(), "Generated review HTML is stale")
    source = OUTPUT.read_text(encoding="utf-8")
    require("@media" in source, "Responsive review styles are missing")
    require("eventNamespace" in source and "toolProjection" in source, "Review choices are missing")
    parser = ScriptParser()
    parser.feed(source)
    executable = [script for attrs, script in parser.scripts if attrs.get("type") != "application/json"]
    require(len(executable) == 1, "Expected one executable review script")
    require(shutil.which("node") is not None, "node is required for JavaScript syntax validation")
    with tempfile.TemporaryDirectory() as directory:
        script = Path(directory) / "review.js"
        script.write_text(executable[0], encoding="utf-8")
        run(["node", "--check", str(script)])


def diagram_names() -> list[str]:
    source = PUML.read_text(encoding="ascii")
    names = re.findall(r"^@startuml\s+([A-Za-z0-9_]+)\s*$", source, re.MULTILINE)
    require(names == ["public_chat_event_boundary", "public_chat_event_projection"],
            "Unexpected PlantUML diagram inventory")
    return names


def validate_diagrams() -> None:
    names = diagram_names()
    for name in names:
        ET.parse(PUML.parent / f"{name}.svg")
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory) / "diagram.puml"
        shutil.copy2(PUML, temporary)
        run(["plantuml", "-tsvg", temporary.name], temporary.parent)
        for name in names:
            require((temporary.parent / f"{name}.svg").read_bytes() ==
                    (PUML.parent / f"{name}.svg").read_bytes(), f"Generated SVG is stale: {name}.svg")


def validate_markdown() -> None:
    for markdown in REPOSITORY_ROOT.rglob("*.md"):
        require("```mermaid" not in markdown.read_text(encoding="utf-8").lower(),
                f"Mermaid block found: {markdown}")
    text = DESIGN.read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)]+\.svg)\)", text):
        require((DESIGN.parent / target).is_file(), f"Missing Markdown SVG: {target}")
    lines = PUML.read_text(encoding="ascii").splitlines()
    for target, raw_line in re.findall(r"\]\(([^)#]+\.puml)#L([1-9][0-9]*)\)", text):
        source = (DESIGN.parent / target).resolve()
        require(source == PUML.resolve(), f"Unexpected PlantUML source: {target}")
        line = int(raw_line)
        require(line <= len(lines) and lines[line - 1].startswith("@startuml"),
                f"Invalid PlantUML line anchor: {target}#L{line}")


def main() -> None:
    model = json.loads(MODEL.read_text(encoding="utf-8"))
    validate_model(model)
    validate_html()
    validate_diagrams()
    validate_markdown()
    run(["git", "diff", "--check"], REPOSITORY_ROOT)
    print("All mate-service Chat events design validations passed.")


if __name__ == "__main__":
    main()

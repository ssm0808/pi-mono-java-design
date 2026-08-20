#!/usr/bin/env python3
"""Validate the source-first Runtime HTTP contract and its generated artifacts."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from render_chat_http_v1 import build_html, load_contract


ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = ROOT.parent
HTML_PATH = ROOT / "chat-http-v1-review.html"
DESIGN_PATH = ROOT / "chat-http-v1-design.md"
CONTRACT_ROOT = ROOT / "contract"
EXPECTED_OPERATION_COUNT = 11
EXPECTED_OPERATIONS = {
    ("POST", "/agents/{agent_id}/sessions"),
    ("GET", "/sessions/{session_id}"),
    ("DELETE", "/sessions/{session_id}"),
    ("POST", "/sessions/{session_id}/events"),
    ("GET", "/sessions/{session_id}/events"),
    ("GET", "/sessions/{session_id}/models"),
    ("PUT", "/sessions/{session_id}/model"),
    ("PUT", "/sessions/{session_id}/thinking"),
    ("POST", "/sessions/{session_id}/steers"),
    ("POST", "/sessions/{session_id}/follow-ups"),
    ("POST", "/sessions/{session_id}/abort"),
}


class ContractHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.static_review_count = 0
        self.styles: list[str] = []
        self.scripts: list[tuple[dict[str, str | None], str]] = []
        self.visible_text: list[str] = []
        self._capture_tag: str | None = None
        self._capture_attrs: dict[str, str | None] = {}
        self._capture_parts: list[str] = []
        self._hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if "data-static-review" in attributes:
            self.static_review_count += 1
        if tag in {"script", "style"}:
            self._capture_tag = tag
            self._capture_attrs = attributes
            self._capture_parts = []
            self._hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag != self._capture_tag:
            return
        source = "".join(self._capture_parts)
        if tag == "script":
            self.scripts.append((self._capture_attrs, source))
        else:
            self.styles.append(source)
        self._capture_tag = None
        self._capture_attrs = {}
        self._capture_parts = []
        self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._capture_tag is not None:
            self._capture_parts.append(data)
        elif self._hidden_depth == 0 and data.strip():
            self.visible_text.append(data.strip())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run(command: list[str], cwd: Path = ROOT) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def read_design_version() -> str:
    content = DESIGN_PATH.read_text(encoding="utf-8")
    match = re.search(r"\| 文档版本 \| ([0-9]+\.[0-9]+\.[0-9]+) \|", content)
    require(match is not None, "Cannot read the design document version")
    return match.group(1)


def validate_common_contract(common: dict[str, Any]) -> None:
    patterns = common.get("resourceIdPatterns", {})
    require(set(patterns) == {"agent", "tool", "skill", "session"}, "Typed resource ID patterns are incomplete")
    valid_ids = {
        "agent": "agent-550e8400e29b41d4a716446655440000",
        "tool": "tool-550e8400e29b41d4a716446655440002",
        "skill": "skill-550e8400e29b41d4a716446655440001",
        "session": "session-550e8400e29b41d4a716446655440003",
    }
    for resource_type, pattern in patterns.items():
        require(re.fullmatch(pattern, valid_ids[resource_type]) is not None, f"Invalid {resource_type} ID pattern")
        legacy_id = valid_ids[resource_type].replace("-", "_", 1)
        require(re.fullmatch(pattern, legacy_id) is None, f"{resource_type} pattern accepts a legacy prefix")
        hyphenated_id = f"{resource_type}-550e8400-e29b-41d4-a716-446655440000"
        require(re.fullmatch(pattern, hyphenated_id) is None, f"{resource_type} pattern accepts UUID hyphens")
    agent_parameter = common["parameters"]["agentId"]
    require(
        agent_parameter["schema"] == {"$ref": "resourceIdPatterns.agent"},
        "Agent path parameter must reference the single Agent ID rule",
    )
    session_parameter = common["parameters"]["sessionId"]
    require(
        session_parameter["schema"] == {"$ref": "resourceIdPatterns.session"},
        "Session path parameter must reference the single Session ID rule",
    )
    header_examples = common.get("requestHeaderExamples", [])
    require(len(header_examples) == 2, "Shared request header examples are incomplete")
    require("互斥检查" in json.dumps(header_examples, ensure_ascii=False),
            "Request header contract must state that Runtime does not reject coexistence")


def parse_generated_models(parser: ContractHtmlParser) -> tuple[list[dict[str, Any]], list[str]]:
    model_arrays = []
    executable_scripts = []
    for attributes, source in parser.scripts:
        if attributes.get("type") == "application/json" and attributes.get("id") == "api-review-models":
            model_arrays.append(json.loads(source))
        elif attributes.get("type") != "application/json":
            executable_scripts.append(source)
    require(len(model_arrays) == 1, "HTML must contain exactly one aggregated review model")
    require(isinstance(model_arrays[0], list), "Aggregated review model must be an array")
    return model_arrays[0], executable_scripts


def validate_html(models: list[dict[str, Any]]) -> None:
    html_source = HTML_PATH.read_text(encoding="utf-8")
    require(html_source == build_html(), "Generated HTML is out of date; run render_chat_http_v1.py")
    parser = ContractHtmlParser()
    parser.feed(html_source)
    embedded_models, scripts = parse_generated_models(parser)
    require(embedded_models == models, "Embedded HTML models differ from contract sources")
    require(parser.static_review_count == EXPECTED_OPERATION_COUNT, "Static no-script operation count is wrong")
    require(len(parser.styles) == 1, "HTML must contain exactly one shared style block")
    require(len(scripts) == 1, "HTML must contain exactly one shared executable script")
    validate_executable_script(scripts[0])
    visible_text = " ".join(parser.visible_text)
    for heading in ("作用", "调用上下文 Header", "参数与请求体", "响应"):
        require(heading in visible_text, f"No-JavaScript contract is missing {heading}")
    require(len(visible_text) > 10000, "No-JavaScript contract content is unexpectedly small")
    require(re.search(r"@media\s*\(max-width:\s*680px\)", html_source) is not None,
            "Responsive breakpoint for a 360px viewport is missing")
    require(re.search(r"content:\s*attr\(data-label\)", html_source) is not None,
            "Responsive labeled table rows are missing")
    require("traceparent" not in html_source, "Forbidden traceparent found in the HTML contract")
    require(re.search(r"agent_[0-9A-Za-z]{24}", html_source) is None, "Legacy Agent ID found in HTML")
    require("01JY8W6M8D9K4H2Q7P3V5N1R0T" not in html_source, "Legacy Session ID found in HTML")
    require("无需业务认证 Header。" not in visible_text, "An operation unexpectedly omits request headers")
    require("AUTH_CREDENTIAL_CONFLICT" not in html_source,
            "Removed Runtime-local credential conflict remains in HTML")
    require("UNAUTHENTICATED" not in html_source,
            "Removed Runtime-local unauthenticated error remains in HTML")
    require(len(html_source.encode("utf-8")) < 300_000, "Generated HTML unexpectedly exceeds 300 KB")


def validate_executable_script(source: str) -> None:
    with tempfile.TemporaryDirectory() as directory:
        script_path = Path(directory) / "contract.js"
        script_path.write_text(source, encoding="utf-8")
        run(["node", "--check", str(script_path)])


def response_codes(operation: dict[str, Any]) -> set[tuple[str, str]]:
    codes = set()
    for response in operation["responses"]:
        for body in response.get("bodies", {}).values():
            if isinstance(body, dict) and body.get("resCode"):
                codes.add((response["status"], body["resCode"]))
    return codes


def values_for_key(value: Any, key: str):
    if isinstance(value, dict):
        for current_key, current_value in value.items():
            if current_key == key:
                yield current_value
            yield from values_for_key(current_value, key)
    elif isinstance(value, list):
        for item in value:
            yield from values_for_key(item, key)


def validate_review_models(common: dict[str, Any], models: list[dict[str, Any]]) -> None:
    expected_version = read_design_version()
    patterns = common["resourceIdPatterns"]
    operations = set()
    for model in models:
        require(model["api"]["version"] == expected_version, "Contract and design versions differ")
        operation = model["operation"]
        require(operation.get("shortName"), "Operation is missing its visible Chinese short name")
        require(operation.get("operationKey"), "Operation is missing its visible operationKey")
        key = (operation["method"], operation["path"])
        require(key not in operations, f"Duplicate operation: {key}")
        operations.add(key)
        require("已确认" in model["api"]["visibility"], f"Operation is not confirmed: {key}")
        require(len(operation["requestHeaderExamples"]) == 2, f"Request header examples are incomplete: {key}")
        header_names = {
            header["name"]
            for example in operation["requestHeaderExamples"]
            for header in example["headers"]
        }
        require({"X-HW-ID", "Authorization", "X-HW-APPKEY"} <= header_names,
                f"Integration request headers are incomplete: {key}")
        require(operation["responses"], f"Operation has no responses: {key}")
        validate_response_contract(patterns["agent"], patterns["session"], key, operation)
    require(operations == EXPECTED_OPERATIONS, "Operation inventory differs from the confirmed contract")


def validate_response_contract(
    agent_pattern: str, session_pattern: str, key: tuple[str, str], operation: dict[str, Any]
) -> None:
    for agent_id in values_for_key(operation["responses"], "agent_id"):
        require(isinstance(agent_id, str) and re.fullmatch(agent_pattern, agent_id) is not None,
                f"Invalid Agent ID response example: {key}")
    for session_id in values_for_key(operation["responses"], "session_id"):
        require(isinstance(session_id, str) and re.fullmatch(session_pattern, session_id) is not None,
                f"Invalid Session ID response example: {key}")
    require(all(response["status"] != "403" for response in operation["responses"]),
            f"Service-local FORBIDDEN response is not implemented: {key}")
    for response in operation["responses"]:
        if response["status"] in {"200", "201", "202", "204"}:
            continue
        for body in response.get("bodies", {}).values():
            if isinstance(body, dict):
                require("result" not in body, f"Error response contains result: {key}")
    codes = response_codes(operation)
    forbidden_auth_codes = {("401", "UNAUTHENTICATED"), ("401", "AUTH_CREDENTIAL_CONFLICT")}
    require(not (forbidden_auth_codes & codes), f"Runtime-local authentication error is forbidden: {key}")
    if key == ("POST", "/agents/{agent_id}/sessions"):
        validate_create_session(agent_pattern, session_pattern, operation)
    elif key == ("DELETE", "/sessions/{session_id}"):
        require(("409", "SESSION_BUSY") in codes, "Delete Session must reject active execution")
    elif key == ("POST", "/sessions/{session_id}/events"):
        require(("503", "RUNTIME_CAPACITY_EXCEEDED") in codes, "POST Events is missing runtime capacity")
        require("[File IDs]" in operation["requestBody"]["description"], "POST Events must define file ID encoding")
        require(set(operation["requestBody"]["example"]) == {"message", "file_ids"},
                "POST Events request must contain only message and file_ids")
        require("type=user.message" not in operation["requestBody"]["description"],
                "POST Events request still documents a redundant type field")
        success = next(response for response in operation["responses"] if response["status"] == "200")
        stream = success["bodies"]["default"]
        for event_type in (
            "assistant.thinking.started", "assistant.thinking.delta", "assistant.thinking.completed"
        ):
            require(f"event: {event_type}" in stream, f"POST Events is missing {event_type}")
        require("\"entry_seq\":18" in stream and "\"type\":\"thinking\"" in stream,
                "Completed thinking must be a durable recoverable event")
    elif key == ("GET", "/sessions/{session_id}/events"):
        success = next(response for response in operation["responses"] if response["status"] == "200")
        event_types = {event["type"] for event in success["bodies"]["en-US"]["result"]["events"]}
        require("assistant.thinking.completed" in event_types,
                "GET Events must show the thinking=true projection")
        require("thinking=false" in operation["description"] and "旧 page 无效" in operation["description"],
                "GET Events must define current-thinking filtering and cursor invalidation")
    elif key in {("POST", "/sessions/{session_id}/steers"), ("POST", "/sessions/{session_id}/follow-ups")}:
        require(("429", "CONTROL_QUEUE_FULL") in codes, f"Control queue limit is missing: {key}")


def validate_create_session(agent_pattern: str, session_pattern: str, operation: dict[str, Any]) -> None:
    parameter = next((item for item in operation["parameters"] if item["name"] == "agent_id"), None)
    require(parameter is not None and parameter["schema"] == agent_pattern, "Create Session Agent ID rule differs")
    created = next((item for item in operation["responses"] if item["status"] == "201"), None)
    require(created is not None, "Create Session is missing 201")
    result = created["bodies"]["en-US"]["result"]
    require(re.fullmatch(session_pattern, result.get("session_id", "")) is not None,
            "Create Session response must use the typed Session ID rule")
    location = created.get("headers", {}).get("Location", "")
    require(location.endswith("/" + result["session_id"]), "Create Session Location differs from session_id")
    require(result.get("thinking") is True, "Create Session must initialize thinking=true")


def validate_source_deduplication() -> None:
    for operation_path in sorted((CONTRACT_ROOT / "operations").glob("*.json")):
        source = json.loads(operation_path.read_text(encoding="utf-8"))
        operation = source["operation"]
        require("requestHeaderExamples" not in operation,
                f"Shared request headers duplicated in {operation_path.name}")
        references = [item.get("$ref") for item in operation["responses"] if isinstance(item, dict)]
        require("responses.unauthenticated" not in references,
                f"Runtime-local authentication error found in {operation_path.name}")
        require("responses.authCredentialConflict" not in references,
                f"Runtime-local credential conflict found in {operation_path.name}")


def diagram_sources() -> list[Path]:
    sources = sorted((ROOT / "diagrams").glob("*/diagram.puml"))
    require(sources, "No topic PlantUML sources found")
    require(not (ROOT / "diagram.puml").exists(), "Legacy aggregate diagram.puml still exists")
    return sources


def diagram_names(source: Path) -> list[str]:
    content = source.read_text(encoding="ascii")
    names = re.findall(r"^@startuml\s+([A-Za-z0-9_]+)\s*$", content, re.MULTILINE)
    require(names, f"No named diagrams in {source.relative_to(ROOT)}")
    return names


def validate_diagram_inventory(sources: list[Path]) -> None:
    for source in sources:
        require(source.read_bytes().isascii(), f"Non-ASCII PlantUML: {source.relative_to(ROOT)}")
        expected = {f"{name}.svg" for name in diagram_names(source)}
        actual = {path.name for path in source.parent.glob("*.svg")}
        require(actual == expected, f"SVG inventory differs in {source.parent.relative_to(ROOT)}")
        for svg_path in source.parent.glob("*.svg"):
            ET.parse(svg_path)


def changed_repository_paths() -> set[Path]:
    commands = [
        ["git", "diff", "--name-only"],
        ["git", "diff", "--cached", "--name-only"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]
    paths = set()
    for command in commands:
        completed = subprocess.run(command, cwd=REPOSITORY_ROOT, check=True, text=True, capture_output=True)
        for line in completed.stdout.splitlines():
            if line:
                paths.add((REPOSITORY_ROOT / line).resolve())
    return paths


def select_diagrams(sources: list[Path], full: bool) -> list[Path]:
    if full:
        return sources
    changed = changed_repository_paths()
    return [source for source in sources if any(path == source or path.parent == source.parent for path in changed)]


def render_and_compare(source: Path) -> None:
    with tempfile.TemporaryDirectory() as directory:
        temporary_root = Path(directory)
        temporary_source = temporary_root / "diagram.puml"
        shutil.copy2(source, temporary_source)
        run(["plantuml", "-tsvg", str(temporary_source)], cwd=temporary_root)
        for name in diagram_names(source):
            generated = (temporary_root / f"{name}.svg").read_bytes()
            checked_in = (source.parent / f"{name}.svg").read_bytes()
            require(generated == checked_in, f"Generated SVG is stale: {source.parent.name}/{name}.svg")


def validate_rendered_diagrams(sources: list[Path]) -> None:
    if not sources:
        return
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(sources))) as executor:
        futures = [executor.submit(render_and_compare, source) for source in sources]
        for future in futures:
            future.result()


def validate_markdown_links() -> None:
    for markdown_path in ROOT.rglob("*.md"):
        content = markdown_path.read_text(encoding="utf-8")
        require("```mermaid" not in content, f"Mermaid is forbidden: {markdown_path.relative_to(ROOT)}")
        for target in re.findall(r"!\[[^\]]*\]\(([^)]+\.svg)\)", content):
            require((markdown_path.parent / target).resolve().exists(), f"Missing SVG link: {target}")
        for target in re.findall(r"\[[^\]]+\]\(([^)#]+\.json)\)", content):
            require((markdown_path.parent / target).resolve().exists(), f"Missing JSON link: {target}")
        anchor_pattern = r"\[[^\]]+\]\(([^)#]+\.puml)#L([0-9]+)\)"
        for target, line_text in re.findall(anchor_pattern, content):
            resolved = (markdown_path.parent / target).resolve()
            require(resolved.exists(), f"Missing PlantUML source: {target}")
            lines = resolved.read_text(encoding="ascii").splitlines()
            line_number = int(line_text)
            require(0 < line_number <= len(lines), f"Invalid PlantUML anchor: {target}#L{line_number}")
            require(lines[line_number - 1].startswith("@startuml"), f"Anchor is not a diagram: {target}#L{line_number}")


def validate_removed_contract() -> None:
    removed_name = "chat-http-v1." + "openapi.yaml"
    require(not (ROOT / removed_name).exists(), "Deprecated OpenAPI file still exists")
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".md", ".html", ".puml", ".py", ".json"}:
            require(removed_name not in path.read_text(encoding="utf-8"),
                    f"Deprecated OpenAPI filename is referenced by {path.relative_to(ROOT)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="render and compare every PlantUML topic")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    common, models = load_contract()
    require(len(models) == EXPECTED_OPERATION_COUNT, f"Expected {EXPECTED_OPERATION_COUNT} operation sources")
    validate_common_contract(common)
    validate_source_deduplication()
    validate_review_models(common, models)
    validate_html(models)
    sources = diagram_sources()
    validate_diagram_inventory(sources)
    selected = select_diagrams(sources, args.full)
    validate_rendered_diagrams(selected)
    validate_markdown_links()
    validate_removed_contract()
    run(["git", "diff", "--check"], cwd=REPOSITORY_ROOT)
    mode = "full" if args.full else "fast"
    print(f"Source-first API contract validation passed: {len(models)} operations, {len(selected)} diagram topics ({mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

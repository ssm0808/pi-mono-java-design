#!/usr/bin/env python3

import json
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HTML_PATH = ROOT / "chat-http-v1-review.html"
DESIGN_PATH = ROOT / "chat-http-v1-design.md"
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
    def __init__(self):
        super().__init__()
        self.static_review_count = 0
        self.scripts = []
        self.visible_text = []
        self._script_attrs = None
        self._script_parts = []
        self._hidden_depth = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "data-static-review" in attributes:
            self.static_review_count += 1
        if tag == "script":
            self._script_attrs = attributes
            self._script_parts = []
            self._hidden_depth += 1
        elif tag == "style":
            self._hidden_depth += 1

    def handle_endtag(self, tag):
        if tag == "script":
            self.scripts.append((self._script_attrs or {}, "".join(self._script_parts)))
            self._script_attrs = None
            self._script_parts = []
            self._hidden_depth -= 1
        elif tag == "style":
            self._hidden_depth -= 1

    def handle_data(self, data):
        if self._script_attrs is not None:
            self._script_parts.append(data)
        elif self._hidden_depth == 0 and data.strip():
            self.visible_text.append(data.strip())


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run(command, cwd=ROOT):
    subprocess.run(command, cwd=cwd, check=True)


def read_design_version():
    match = re.search(r"\| 文档版本 \| ([0-9]+\.[0-9]+\.[0-9]+) \|", DESIGN_PATH.read_text())
    require(match is not None, "Cannot read the design document version")
    return match.group(1)


def validate_html():
    html = HTML_PATH.read_text()
    parser = ContractHtmlParser()
    parser.feed(html)

    models = []
    executable_scripts = []
    for attributes, source in parser.scripts:
        if attributes.get("type") == "application/json" and "data-review-model" in attributes:
            models.append(json.loads(source))
        elif attributes.get("type") != "application/json":
            executable_scripts.append(source)

    require(parser.static_review_count == EXPECTED_OPERATION_COUNT,
            f"Expected {EXPECTED_OPERATION_COUNT} static operations")
    require(len(models) == EXPECTED_OPERATION_COUNT,
            f"Expected {EXPECTED_OPERATION_COUNT} review models")
    validate_review_models(models)
    validate_executable_scripts(executable_scripts)

    visible_text = " ".join(parser.visible_text)
    for heading in ("作用", "认证", "参数与请求体", "响应"):
        require(heading in visible_text, f"No-JavaScript contract is missing {heading}")
    require(len(visible_text) > 10000, "No-JavaScript contract content is unexpectedly small")
    require(re.search(r"@media\s*\(max-width:\s*680px\)", html) is not None,
            "Responsive breakpoint for a 360px viewport is missing")
    require(re.search(r"content:\s*attr\(data-label\)", html) is not None,
            "Responsive labeled table rows are missing")
    require("traceparent" not in html, "Forbidden traceparent found in the HTML contract")
    return models


def validate_review_models(models):
    expected_version = read_design_version()
    operations = set()
    for model in models:
        api = model.get("api", {})
        operation = model.get("operation", {})
        key = (operation.get("method"), operation.get("path"))
        require(None not in key, "Review model has no method or path")
        require(key not in operations, f"Duplicate operation: {key}")
        operations.add(key)
        require(api.get("version") == expected_version,
                f"HTML version does not match design version for {key}")
        require("已确认" in api.get("visibility", ""), f"Operation is not confirmed: {key}")
        require(operation.get("description"), f"Operation has no purpose: {key}")
        require(len(operation.get("authModes", [])) == 2, f"Authentication modes are incomplete: {key}")
        require(operation.get("responses"), f"Operation has no responses: {key}")
        validate_response_contract(key, operation)
    require(operations == EXPECTED_OPERATIONS, "HTML operation set does not match the confirmed contract")


def response_codes(operation):
    codes = set()
    for response in operation["responses"]:
        for body in response.get("bodies", {}).values():
            if isinstance(body, dict) and body.get("resCode"):
                codes.add((response.get("status"), body["resCode"]))
    return codes


def validate_response_contract(key, operation):
    require(all(response.get("status") != "403" for response in operation["responses"]),
            f"Service-local FORBIDDEN response is not implemented: {key}")
    for response in operation["responses"]:
        if response.get("status") in {"200", "201", "202", "204"}:
            continue
        for body in response.get("bodies", {}).values():
            if isinstance(body, dict):
                require("result" not in body, f"Error response contains result: {key}")
    codes = response_codes(operation)
    if key == ("DELETE", "/sessions/{session_id}"):
        require(("409", "SESSION_BUSY") in codes, "Delete Session must reject active execution")
    elif key == ("POST", "/sessions/{session_id}/events"):
        require(("503", "RUNTIME_CAPACITY_EXCEEDED") in codes,
                "POST Events is missing the runtime capacity response")
        require("[File IDs]" in operation["requestBody"]["description"],
                "POST Events must document raw file ID prompt encoding")
    elif key in {
        ("POST", "/sessions/{session_id}/steers"),
        ("POST", "/sessions/{session_id}/follow-ups"),
    }:
        require(("429", "CONTROL_QUEUE_FULL") in codes,
                f"Control operation is missing the bounded queue response: {key}")


def validate_executable_scripts(scripts):
    require(len(scripts) == EXPECTED_OPERATION_COUNT,
            f"Expected {EXPECTED_OPERATION_COUNT} executable scripts")
    with tempfile.TemporaryDirectory() as directory:
        for index, source in enumerate(scripts):
            path = Path(directory) / f"contract-{index}.js"
            path.write_text(source)
            run(["node", "--check", str(path)])


def validate_plantuml_and_svg():
    puml_paths = sorted(ROOT.rglob("*.puml"))
    require(puml_paths, "No PlantUML sources found")
    for path in puml_paths:
        require(path.read_bytes().isascii(), f"Non-ASCII PlantUML content: {path.relative_to(ROOT)}")
        run(["plantuml", "-tsvg", str(path)])
    for path in ROOT.rglob("*.svg"):
        ET.parse(path)


def validate_markdown_links():
    for markdown_path in ROOT.rglob("*.md"):
        content = markdown_path.read_text()
        require("```mermaid" not in content, f"Mermaid is forbidden: {markdown_path.relative_to(ROOT)}")
        for target in re.findall(r"!\[[^\]]*\]\(([^)]+\.svg)\)", content):
            resolved = (markdown_path.parent / target).resolve()
            require(resolved.exists(), f"Missing SVG link: {target} in {markdown_path.name}")
        pattern = r"\[[^\]]+\]\(([^)#]+\.puml)#L([0-9]+)\)"
        for target, line_text in re.findall(pattern, content):
            resolved = (markdown_path.parent / target).resolve()
            require(resolved.exists(), f"Missing PlantUML source: {target}")
            lines = resolved.read_text().splitlines()
            line_number = int(line_text)
            require(0 < line_number <= len(lines), f"Invalid PlantUML line anchor: {target}#L{line_number}")
            require(lines[line_number - 1].startswith("@startuml"),
                    f"PlantUML anchor does not point to a diagram: {target}#L{line_number}")


def validate_removed_contract():
    removed_name = "chat-http-v1." + "openapi.yaml"
    require(not (ROOT / removed_name).exists(), "Deprecated OpenAPI file still exists")
    for path in ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".md", ".html", ".puml", ".py"}:
            require(removed_name not in path.read_text(),
                    f"Deprecated OpenAPI filename is still referenced by {path.relative_to(ROOT)}")


def main():
    models = validate_html()
    validate_removed_contract()
    validate_plantuml_and_svg()
    validate_markdown_links()
    run(["git", "diff", "--check"])
    print(f"HTML-first API contract validation passed: {len(models)} operations")


if __name__ == "__main__":
    main()

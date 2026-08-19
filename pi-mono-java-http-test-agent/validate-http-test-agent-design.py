#!/usr/bin/env python3
"""Validate the Runtime HTTP test-agent design and its machine catalog."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET


TOPIC_DIR = Path(__file__).resolve().parent
REPO_DIR = TOPIC_DIR.parent
README = TOPIC_DIR / "README.md"
CATALOG = TOPIC_DIR / "test-case-catalog.json"
PUML = TOPIC_DIR / "diagram.puml"

EXPECTED_OPERATIONS = [
    ("createSession", "创建会话", "POST", "/campusclaw-service/v1/agents/{agent_id}/sessions"),
    ("getSession", "查询会话", "GET", "/campusclaw-service/v1/sessions/{session_id}"),
    ("deleteSession", "删除会话", "DELETE", "/campusclaw-service/v1/sessions/{session_id}"),
    ("submitUserMessage", "提交用户消息", "POST", "/campusclaw-service/v1/sessions/{session_id}/events"),
    ("listSessionEvents", "查询会话事件", "GET", "/campusclaw-service/v1/sessions/{session_id}/events"),
    ("listSessionModels", "查询可用模型", "GET", "/campusclaw-service/v1/sessions/{session_id}/models"),
    ("changeSessionModel", "切换会话模型", "PUT", "/campusclaw-service/v1/sessions/{session_id}/model"),
    ("changeSessionThinking", "设置深度思考", "PUT", "/campusclaw-service/v1/sessions/{session_id}/thinking"),
    ("appendSteer", "追加引导消息", "POST", "/campusclaw-service/v1/sessions/{session_id}/steers"),
    ("appendFollowUp", "追加后续消息", "POST", "/campusclaw-service/v1/sessions/{session_id}/follow-ups"),
    ("abortSession", "中止会话执行", "POST", "/campusclaw-service/v1/sessions/{session_id}/abort"),
]
EXPECTED_BLOCKS = [
    "http_test_agent_architecture",
    "http_test_execution_sequence",
    "http_test_case_maintenance",
]
VALID_PRIORITIES = {"P0", "P1", "P2"}
VALID_STATUSES = {"active", "proposed", "retired"}
VALID_LAYERS = {
    "static",
    "mvc",
    "service",
    "database",
    "process",
    "concurrency",
    "recovery",
    "compatibility",
}


class ReviewModelParser(HTMLParser):
    """Collect JSON text from script elements carrying data-review-model."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._capturing = False
        self._parts: list[str] = []
        self.models: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script" and any(name == "data-review-model" for name, _ in attrs):
            self._capturing = True
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._capturing:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._capturing:
            self.models.append(json.loads("".join(self._parts)))
            self._capturing = False
            self._parts = []


def fail(message: str) -> None:
    raise ValueError(message)


def read_contract_text(contract_path: Path, contract_ref: str | None) -> str:
    if contract_ref is None:
        return contract_path.read_text(encoding="utf-8")
    relative_path = contract_path.relative_to(REPO_DIR).as_posix()
    result = subprocess.run(
        ["git", "show", f"{contract_ref}:{relative_path}"],
        cwd=REPO_DIR,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def validate_contract(catalog: dict, contract_ref: str | None) -> None:
    contract = catalog["contract"]
    contract_path = (TOPIC_DIR / contract["reviewDocument"]).resolve()
    parser = ReviewModelParser()
    parser.feed(read_contract_text(contract_path, contract_ref))
    if len(parser.models) != contract["expectedOperationCount"]:
        fail(f"review model count is {len(parser.models)}, expected {contract['expectedOperationCount']}")

    versions = {model["api"]["version"] for model in parser.models}
    if versions != {contract["version"]}:
        fail(f"contract version drift: review models={sorted(versions)}, catalog={contract['version']}")
    base_paths = {model["api"]["basePath"] for model in parser.models}
    if base_paths != {"/campusclaw-service/v1"}:
        fail(f"unexpected API base paths: {sorted(base_paths)}")

    extracted = [
        (
            model["operation"]["operationKey"],
            model["operation"]["shortName"],
            model["operation"]["method"],
            model["api"]["basePath"] + model["operation"]["path"],
        )
        for model in parser.models
    ]
    expected = EXPECTED_OPERATIONS
    if extracted != expected:
        fail(f"review operation inventory differs from expected order: {extracted}")


def iter_cases(catalog: dict):
    for case in catalog["globalTemplates"]:
        yield "globalTemplates", case
    for operation in catalog["operations"]:
        for case in operation["cases"]:
            yield operation["operationKey"], case
    for case in catalog["crossOperationCases"]:
        yield "crossOperationCases", case
    for case in catalog["proposedCases"]:
        yield "proposedCases", case


def validate_catalog(catalog: dict) -> None:
    if catalog["catalogVersion"] != "1.0.0":
        fail("catalogVersion must match the design document version 1.0.0")
    operations = [
        (item["operationKey"], item["shortName"], item["method"], item["path"])
        for item in catalog["operations"]
    ]
    if operations != EXPECTED_OPERATIONS:
        fail(f"catalog operation inventory differs from the frozen 11 operations: {operations}")

    evidence = set(catalog["evidenceRegistry"])
    seen: set[str] = set()
    for owner, case in iter_cases(catalog):
        case_id = case.get("id", "")
        if not re.fullmatch(r"HTA-[A-Z0-9-]+", case_id):
            fail(f"invalid case ID in {owner}: {case_id!r}")
        if case_id in seen:
            fail(f"duplicate case ID: {case_id}")
        seen.add(case_id)
        if case.get("priority") not in VALID_PRIORITIES:
            fail(f"invalid priority for {case_id}: {case.get('priority')}")
        if case.get("layer") not in VALID_LAYERS:
            fail(f"invalid layer for {case_id}: {case.get('layer')}")
        status = case.get("status", "active" if owner == "globalTemplates" else None)
        if status not in VALID_STATUSES:
            fail(f"invalid status for {case_id}: {status}")
        if not case.get("oracle") and status == "active":
            fail(f"active case has no deterministic oracle: {case_id}")
        for reference in case.get("evidenceRefs", []):
            if reference not in evidence:
                fail(f"unknown evidence reference {reference} in {case_id}")

    for operation in catalog["operations"]:
        if not operation["cases"]:
            fail(f"operation has no cases: {operation['operationKey']}")
        for reference in operation.get("evidenceRefs", []):
            if reference not in evidence:
                fail(f"unknown operation evidence reference: {reference}")


def validate_markdown_and_diagrams(render: bool) -> None:
    markdown = README.read_text(encoding="utf-8")
    puml_text = PUML.read_text(encoding="ascii")
    if any("```mermaid" in path.read_text(encoding="utf-8").lower() for path in TOPIC_DIR.glob("*.md")):
        fail("Mermaid is prohibited in design Markdown")

    blocks: list[tuple[str, int]] = []
    for line_number, line in enumerate(puml_text.splitlines(), start=1):
        match = re.fullmatch(r"@startuml\s+([A-Za-z0-9_]+)", line)
        if match:
            blocks.append((match.group(1), line_number))
    if [name for name, _ in blocks] != EXPECTED_BLOCKS:
        fail(f"unexpected PlantUML blocks: {blocks}")

    anchors = [int(value) for value in re.findall(r"\(diagram\.puml#L(\d+)\)", markdown)]
    if anchors != [line_number for _, line_number in blocks]:
        fail(f"PlantUML source anchors {anchors} do not match block lines {blocks}")

    referenced_svgs = re.findall(r"!\[[^]]*\]\(([^)]+\.svg)\)", markdown)
    expected_svgs = [f"{name}.svg" for name, _ in blocks]
    if referenced_svgs != expected_svgs:
        fail(f"Markdown SVG references {referenced_svgs} do not match blocks {expected_svgs}")

    if render:
        subprocess.run(["plantuml", "-tsvg", PUML.name], cwd=TOPIC_DIR, check=True)
    for svg_name in expected_svgs:
        svg_path = TOPIC_DIR / svg_name
        if not svg_path.is_file():
            fail(f"missing generated SVG: {svg_name}")
        ET.parse(svg_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--contract-ref",
        help="read the canonical review HTML from this Git ref instead of the working tree",
    )
    parser.add_argument("--no-render", action="store_true", help="validate existing SVG files without regenerating")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        validate_catalog(catalog)
        validate_contract(catalog, args.contract_ref)
        validate_markdown_and_diagrams(not args.no_render)
    except (KeyError, OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError, ET.ParseError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(
        f"PASS: {len(catalog['operations'])} operations, "
        f"{sum(1 for _ in iter_cases(catalog))} catalog entries, "
        f"{len(EXPECTED_BLOCKS)} synchronized PlantUML diagrams"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

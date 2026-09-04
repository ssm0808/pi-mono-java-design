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
REPOSITORY_ROOT = ROOT.parents[1]
HTML_PATH = ROOT / "chat-http-v1-review.html"
DESIGN_PATH = ROOT / "chat-http-v1-design.md"
CONTRACT_ROOT = ROOT / "接口契约"
SLASH_DESIGN_PATHS = (
    REPOSITORY_ROOT / "04-命令与技能/00-Slash-Command通用模块/README.md",
    REPOSITORY_ROOT / "04-命令与技能/01-内置命令/README.md",
    REPOSITORY_ROOT / "04-命令与技能/02-技能命令/README.md",
)
EXPECTED_OPERATION_COUNT = 13
EXPECTED_OPERATIONS = {
    ("POST", "/agents/{agentId}/sessions"),
    ("GET", "/sessions/{sessionId}"),
    ("DELETE", "/sessions/{sessionId}"),
    ("POST", "/sessions/{sessionId}/events"),
    ("GET", "/sessions/{sessionId}/events"),
    ("GET", "/sessions/{sessionId}/models"),
    ("PUT", "/sessions/{sessionId}/model"),
    ("PUT", "/sessions/{sessionId}/thinking"),
    ("POST", "/sessions/{sessionId}/steers"),
    ("POST", "/sessions/{sessionId}/follow-ups"),
    ("POST", "/sessions/{sessionId}/abort"),
    ("GET", "/sessions/{sessionId}/commands"),
    ("POST", "/sessions/{sessionId}/command"),
}
EXPECTED_CONTEXT_HEADERS = {"X-HW-ID", "Authorization", "X-HW-APPKEY"}
POST_EVENTS = ("POST", "/sessions/{sessionId}/events")
POST_COMMAND = ("POST", "/sessions/{sessionId}/command")
POST_EVENTS_CONTEXT_HEADERS = EXPECTED_CONTEXT_HEADERS | {"access-token"}
EXPECTED_SHARED_HEADER_VALUES = {
    "jwt": {"X-HW-ID": "credential-jwt", "Authorization": "Bearer opaque-token"},
    "appkey": {"X-HW-ID": "credential-appkey", "X-HW-APPKEY": "opaque-appkey"},
}
EXPECTED_EXECUTION_HEADER_VALUES = {
    mode: values | {"access-token": "opaque-access-token"}
    for mode, values in EXPECTED_SHARED_HEADER_VALUES.items()
}
EXPECTED_PARAMETER_HEADERS = {"Accept-Language", "If-Match"}
LOWER_CAMEL_FIELD = re.compile(r"^[a-z][A-Za-z0-9]*$")


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


def validate_header_examples(
    examples: list[dict[str, Any]], expected_values: dict[str, dict[str, str]], context: str
) -> None:
    require({example.get("id") for example in examples} == set(expected_values),
            f"{context} request Header modes are incomplete")
    for example in examples:
        headers = {header["name"]: header for header in example["headers"]}
        actual_values = {name: header.get("value") for name, header in headers.items()}
        require(actual_values == expected_values[example["id"]],
                f"{context} request Header values differ: {example['id']}")
        require(all(header.get("required") is True for header in headers.values()),
                f"{context} request Header requiredness differs: {example['id']}")
        x_hw_id_description = headers["X-HW-ID"].get("description", "")
        require("用户凭据 ID" in x_hw_id_description and "不是公司、服务或应用标识" in x_hw_id_description,
                f"{context} must define X-HW-ID as the user credential ID")
        serialized = json.dumps(example, ensure_ascii=False)
        for forbidden in ("公司调用方标识", "瞬态", "瞬时", "<CALLER_ID>", "<JWT>", "<APPKEY>",
                          "<ACCESS_TOKEN>"):
            require(forbidden not in serialized, f"{context} contains obsolete Header wording: {forbidden}")
        if "access-token" in headers:
            for header in headers.values():
                description = header.get("description", "")
                for phrase in ("只在内存中保留到本次", "Mate tool execute", "不写入 Session、事件或日志"):
                    require(phrase in description,
                            f"{context} execution Header description is incomplete: {phrase}")


def read_design_version() -> str:
    content = DESIGN_PATH.read_text(encoding="utf-8")
    match = re.search(r"\| 文档版本 \| ([0-9]+\.[0-9]+\.[0-9]+) \|", content)
    require(match is not None, "Cannot read the design document version")
    return match.group(1)


def validate_common_contract(common: dict[str, Any]) -> None:
    api = common.get("api", {})
    require(api.get("fieldNaming") == "lowerCamelCase", "Public field naming rule must be lowerCamelCase")
    require(api.get("headerNaming") == "保留原名", "HTTP Header naming rule must preserve existing names")
    patterns = common.get("resourceIdPatterns", {})
    require(
        set(patterns) == {"agent", "tool", "skill", "session"},
        "Typed resource ID patterns are incomplete",
    )
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
    command_names = common.get("commandNamePatterns", {})
    require(set(command_names) == {"builtin"}, "Command name patterns are incomplete")
    require(re.fullmatch(command_names["builtin"], "status") is not None, "Builtin name pattern is invalid")
    require(re.fullmatch(command_names["builtin"], "Status") is None, "Builtin names must be lowercase")
    for invalid_name in ("-status", "status-", "session--status", "skill:pdf", "Status"):
        require(re.fullmatch(command_names["builtin"], invalid_name) is None,
                f"Builtin name pattern accepts an invalid name: {invalid_name}")
    require(common.get("commandLimits") == {
        "builtinNameCharacters": 64,
        "argumentsUtf16CodeUnits": 262144,
    }, "Command limits differ from the confirmed contract")
    agent_parameter = common["parameters"]["agentId"]
    require(agent_parameter["name"] == "agentId", "Agent path parameter must use lowerCamelCase")
    require(
        agent_parameter["schema"] == {"$ref": "resourceIdPatterns.agent"},
        "Agent path parameter must reference the single Agent ID rule",
    )
    session_parameter = common["parameters"]["sessionId"]
    require(session_parameter["name"] == "sessionId", "Session path parameter must use lowerCamelCase")
    require(
        session_parameter["schema"] == {"$ref": "resourceIdPatterns.session"},
        "Session path parameter must reference the single Session ID rule",
    )
    header_examples = common.get("requestHeaderExamples", [])
    require(len(header_examples) == 2, "Shared request header examples are incomplete")
    header_names = {
        header["name"]
        for example in header_examples
        for header in example["headers"]
    }
    require(header_names == EXPECTED_CONTEXT_HEADERS, "Shared HTTP Header names changed unexpectedly")
    validate_header_examples(header_examples, EXPECTED_SHARED_HEADER_VALUES, "Shared")
    require("可与 Authorization 同时提供" in json.dumps(header_examples, ensure_ascii=False),
            "Request header contract must state that both credential modes may be provided")


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
    require("字段：lowerCamelCase" in visible_text, "HTML does not expose the public field naming rule")
    require("Header：保留原名" in visible_text, "HTML does not expose the preserved Header naming rule")
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
    require(len(html_source.encode("utf-8")) < 500_000, "Generated HTML unexpectedly exceeds 500 KB")


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
        expected_headers = (
            POST_EVENTS_CONTEXT_HEADERS
            if key in {POST_EVENTS, POST_COMMAND}
            else EXPECTED_CONTEXT_HEADERS
        )
        require(header_names == expected_headers, f"Integration request Header names changed: {key}")
        expected_values = (
            EXPECTED_EXECUTION_HEADER_VALUES
            if key in {POST_EVENTS, POST_COMMAND}
            else EXPECTED_SHARED_HEADER_VALUES
        )
        validate_header_examples(operation["requestHeaderExamples"], expected_values, str(key))
        parameter_headers = {
            parameter["name"] for parameter in operation["parameters"] if parameter["in"] == "header"
        }
        require(parameter_headers <= EXPECTED_PARAMETER_HEADERS, f"Operation request Header names changed: {key}")
        validate_public_field_names(key, operation)
        require(operation["responses"], f"Operation has no responses: {key}")
        validate_response_contract(
            patterns["agent"], patterns["session"], key, operation
        )
    require(operations == EXPECTED_OPERATIONS, "Operation inventory differs from the confirmed contract")


def validate_public_field_names(key: tuple[str, str], operation: dict[str, Any]) -> None:
    placeholders = re.findall(r"{([^}]+)}", operation["path"])
    require(all(LOWER_CAMEL_FIELD.fullmatch(name) for name in placeholders),
            f"Path parameter is not lowerCamelCase: {key}")
    for parameter in operation["parameters"]:
        if parameter["in"] in {"path", "query"}:
            require(LOWER_CAMEL_FIELD.fullmatch(parameter["name"]) is not None,
                    f"Public parameter is not lowerCamelCase: {key} {parameter['name']}")
    request_example = operation["requestBody"].get("example")
    if request_example is not None:
        validate_payload_keys(request_example, f"request example {key}")
    for response in operation["responses"]:
        for locale, body in response.get("bodies", {}).items():
            context = f"response {response['status']} {locale} {key}"
            if isinstance(body, (dict, list)):
                validate_payload_keys(body, context)
            elif isinstance(body, str):
                for field in re.findall(r'"([A-Za-z][A-Za-z0-9_]*)"\s*:', body):
                    require(LOWER_CAMEL_FIELD.fullmatch(field) is not None,
                            f"SSE field is not lowerCamelCase: {context} {field}")


def validate_payload_keys(value: Any, context: str) -> None:
    if isinstance(value, dict):
        for field, nested in value.items():
            require(LOWER_CAMEL_FIELD.fullmatch(field) is not None,
                    f"Payload field is not lowerCamelCase: {context} {field}")
            validate_payload_keys(nested, context)
    elif isinstance(value, list):
        for item in value:
            validate_payload_keys(item, context)


def validate_response_contract(
    agent_pattern: str,
    session_pattern: str,
    key: tuple[str, str],
    operation: dict[str, Any],
) -> None:
    for agent_id in values_for_key(operation["responses"], "agentId"):
        require(isinstance(agent_id, str) and re.fullmatch(agent_pattern, agent_id) is not None,
                f"Invalid Agent ID response example: {key}")
    for session_id in values_for_key(operation["responses"], "sessionId"):
        require(isinstance(session_id, str) and re.fullmatch(session_pattern, session_id) is not None,
                f"Invalid Session ID response example: {key}")
    require(not list(values_for_key(operation["responses"], "commandId")),
            f"Public commandId is forbidden: {key}")
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
    if key == ("POST", "/agents/{agentId}/sessions"):
        validate_create_session(agent_pattern, session_pattern, operation)
    elif key in {
        ("GET", "/sessions/{sessionId}"),
        ("PUT", "/sessions/{sessionId}/model"),
        ("PUT", "/sessions/{sessionId}/thinking"),
    }:
        success = next(response for response in operation["responses"] if response["status"] == "200")
        result = next(body["result"] for body in success["bodies"].values() if isinstance(body, dict))
        require("displayName" in result, f"SessionResource is missing displayName: {key}")
    elif key == ("DELETE", "/sessions/{sessionId}"):
        require(("409", "SESSION_BUSY") in codes, "Delete Session must reject active execution")
    elif key == ("POST", "/sessions/{sessionId}/events"):
        expected_example_headers = {
            "jwt": {"X-HW-ID", "Authorization", "access-token"},
            "appkey": {"X-HW-ID", "X-HW-APPKEY", "access-token"},
        }
        for example in operation["requestHeaderExamples"]:
            names = {header["name"] for header in example["headers"]}
            require(names == expected_example_headers.get(example["id"]),
                    f"POST Events Header mode differs: {example['id']}")
            access_token = next(
                (header for header in example["headers"] if header["name"] == "access-token"), None
            )
            require(access_token is not None and access_token.get("required") is True
                    and access_token.get("value") == "opaque-access-token",
                    "POST Events must require access-token in every request Header example")
        description = operation["description"]
        for required_phrase in ("只在内存中保留到本次 Agent 执行结束", "Mate 工具 execute",
                                "不写入 Session、事件或日志", "工具发现"):
            require(required_phrase in description,
                    f"POST Events credential boundary is incomplete: {required_phrase}")
        require(("503", "RUNTIME_CAPACITY_EXCEEDED") in codes, "POST Events is missing runtime capacity")
        require("[File IDs]" in operation["requestBody"]["description"], "POST Events must define file ID encoding")
        require(set(operation["requestBody"]["example"]) == {"message", "fileIds"},
                "POST Events request must contain only message and fileIds")
        require("type=user.message" not in operation["requestBody"]["description"],
                "POST Events request still documents a redundant type field")
        success = next(response for response in operation["responses"] if response["status"] == "200")
        stream = success["bodies"]["default"]
        for event_type in (
            "assistant.thinking.started", "assistant.thinking.delta", "assistant.thinking.completed"
        ):
            require(f"event: {event_type}" in stream, f"POST Events is missing {event_type}")
        require("\"entrySeq\":18" in stream and "\"type\":\"thinking\"" in stream,
                "Completed thinking must be a durable recoverable event")
    elif key == ("GET", "/sessions/{sessionId}/commands"):
        success = next(response for response in operation["responses"] if response["status"] == "200")
        commands = success["bodies"]["zh-CN"]["result"]["commands"]
        names = [command["name"] for command in commands]
        require(names == ["compact", "help", "model", "name", "skills", "status", "thinking"],
                "Builtin command catalog must contain exactly seven sorted entries")
        require(all(command["kind"] == "builtin" for command in commands),
                "Command catalog must not expose Skill commands")
        require(all(command["input"]["acceptsFiles"] is False for command in commands),
                "Builtin command catalog must reject files")
        require(all(isinstance(command["input"]["suggestions"], list) for command in commands),
                "Catalog suggestions must be non-null lists")
        model = next(command for command in commands if command["name"] == "model")
        require(model["available"] is True and model["input"]["available"] is False,
                "Running model descriptor must separate query and input availability")
        require(model["input"]["unavailableCode"] == "SESSION_BUSY",
                "Running model input must expose SESSION_BUSY")
        require(not any(code == "AGENT_NOT_AVAILABLE" for _, code in response_codes(operation)),
                "Builtin catalog must not depend on an Agent snapshot")
    elif key == ("POST", "/sessions/{sessionId}/command"):
        for phrase in ("只在内存中保留到本次命令处理", "Mate tool execute",
                       "不写入 Session、事件或日志", "工具发现", "Active Holder"):
            require(phrase in operation["description"], f"Missing credential boundary: {phrase}")
        require(set(operation["requestBody"]["example"]) == {"name", "arguments"},
                "POST Command request must contain only name and arguments")
        for phrase in ("262144", "fileIds", "If-Match", "Idempotency-Key"):
            require(phrase in operation["requestBody"]["description"],
                    f"POST Command request contract is incomplete: {phrase}")
        codes = response_codes(operation)
        for expected in {
            ("400", "INVALID_COMMAND_REQUEST"), ("404", "COMMAND_NOT_FOUND"),
            ("409", "SESSION_BUSY"), ("422", "AGENT_NOT_AVAILABLE"),
            ("422", "MODEL_NOT_AVAILABLE"), ("422", "THINKING_NOT_SUPPORTED"),
            ("500", "COMMAND_EXECUTION_FAILED"), ("500", "SESSION_NAME_UPDATE_FAILED"),
            ("503", "MANAGER_UNAVAILABLE"), ("503", "RUNTIME_CAPACITY_EXCEEDED"),
        }:
            require(expected in codes, f"POST Command is missing {expected}")
        successes = [response for response in operation["responses"] if response["status"] == "200"]
        results = [next(iter(response["bodies"].values()))["result"] for response in successes]
        expected_fields = {
            "help": {"command", "commands"},
            "status": {"command", "state", "modelId", "thinking"},
            "name": {"command", "displayName", "changed"},
            "model": {"command", "currentModelId", "models", "changed", "sourceEventSeq"},
            "thinking": {"command", "thinking", "changed", "sourceEventSeq"},
            "compact": {"command", "compacted", "sourceEventSeq"},
            "skills": {"command", "skills"},
        }
        require({result["command"] for result in results} == set(expected_fields),
                "POST Command must document all seven typed success results")
        for result in results:
            require(set(result) == expected_fields[result["command"]], "Unexpected success fields")
        for response in successes:
            require(response["headers"].get("Content-Type") == "application/json",
                    "POST Command success must use ordinary JSON")
            require(response["headers"].get("Cache-Control") == "no-store", "Missing no-store")
            require("default" not in response["bodies"], "POST Command must not contain SSE bodies")
        serialized = json.dumps(operation, ensure_ascii=False)
        require("event: command." not in serialized and "event: stream." not in serialized,
                "POST Command must not expose request-scoped SSE lifecycle events")
    elif key == ("GET", "/sessions/{sessionId}/events"):
        success = next(response for response in operation["responses"] if response["status"] == "200")
        event_types = {event["type"] for event in success["bodies"]["en-US"]["result"]["events"]}
        require("assistant.thinking.completed" in event_types,
                "GET Events must show the thinking=true projection")
        require("thinking=false" in operation["description"] and "旧 page 无效" in operation["description"],
                "GET Events must define current-thinking filtering and cursor invalidation")
    elif key in {("POST", "/sessions/{sessionId}/steers"), ("POST", "/sessions/{sessionId}/follow-ups")}:
        require(("429", "CONTROL_QUEUE_FULL") in codes, f"Control queue limit is missing: {key}")


def validate_create_session(agent_pattern: str, session_pattern: str, operation: dict[str, Any]) -> None:
    parameter = next((item for item in operation["parameters"] if item["name"] == "agentId"), None)
    require(parameter is not None and parameter["schema"] == agent_pattern, "Create Session Agent ID rule differs")
    created = next((item for item in operation["responses"] if item["status"] == "201"), None)
    require(created is not None, "Create Session is missing 201")
    result = created["bodies"]["en-US"]["result"]
    require(re.fullmatch(session_pattern, result.get("sessionId", "")) is not None,
            "Create Session response must use the typed Session ID rule")
    location = created.get("headers", {}).get("Location", "")
    require(location.endswith("/" + result["sessionId"]), "Create Session Location differs from sessionId")
    require(result.get("thinking") is True, "Create Session must initialize thinking=true")
    require("displayName" in result and result["displayName"] is None,
            "Create Session must initialize displayName=null")


def validate_source_deduplication() -> None:
    for operation_path in sorted((CONTRACT_ROOT / "操作").glob("*.json")):
        source = json.loads(operation_path.read_text(encoding="utf-8"))
        operation = source["operation"]
        if operation.get("operationKey") in {"submitUserMessage", "executeSessionCommand"}:
            examples = operation.get("requestHeaderExamples", [])
            header_names = {
                header["name"]
                for example in examples
                for header in example.get("headers", [])
            }
            require(len(examples) == 2 and header_names == POST_EVENTS_CONTEXT_HEADERS,
                    "Execution POST must override shared Header examples only to add access-token")
        else:
            require("requestHeaderExamples" not in operation,
                    f"Shared request headers duplicated in {operation_path.name}")
        references = [item.get("$ref") for item in operation["responses"] if isinstance(item, dict)]
        require("responses.unauthenticated" not in references,
                f"Runtime-local authentication error found in {operation_path.name}")
        require("responses.authCredentialConflict" not in references,
                f"Runtime-local credential conflict found in {operation_path.name}")


def diagram_sources() -> list[Path]:
    sources = sorted((ROOT / "设计图").glob("*/diagram.puml"))
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
        ["git", "-c", "core.quotepath=false", "diff", "--name-only"],
        ["git", "-c", "core.quotepath=false", "diff", "--cached", "--name-only"],
        ["git", "-c", "core.quotepath=false", "ls-files", "--others", "--exclude-standard"],
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


def validate_command_wording(models: list[dict[str, Any]]) -> None:
    for path in SLASH_DESIGN_PATHS:
        require("目录" not in path.read_text(encoding="utf-8"),
                f"Slash Command design must use explicit wording: {path.relative_to(REPOSITORY_ROOT)}")
    design_text = DESIGN_PATH.read_text(encoding="utf-8")
    contract_text = json.dumps(models, ensure_ascii=False)
    for wording in ("命令目录", "列出当前目录", "当前目录中的已知命令", "Skill 父目录", "回退父目录名"):
        require(wording not in design_text, f"Runtime design contains ambiguous Command wording: {wording}")
    for wording in ("命令目录", "列出当前目录", "当前目录中的已知命令"):
        require(wording not in contract_text, f"Runtime contract contains ambiguous Command wording: {wording}")


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
    validate_command_wording(models)
    validate_removed_contract()
    run(["git", "diff", "--check"], cwd=REPOSITORY_ROOT)
    mode = "full" if args.full else "fast"
    print(f"Source-first API contract validation passed: {len(models)} operations, {len(selected)} diagram topics ({mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

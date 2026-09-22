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

from render_chat_http_v1 import build_operation_html, load_contract, contract_text
from command_catalog_contract import validate_catalog_examples
from command_response_contract import validate_response_reuse
from help_review_projection import load_help_model
from request_header_contract import validate_request_headers


ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = ROOT.parents[1]
HTML_PATH = ROOT / "chat-api-review.html"
DESIGN_PATH = ROOT / "chat-http-v1-design.md"
CONTRACT_ROOT = ROOT / "接口契约"
SLASH_DESIGN_PATHS = (
    REPOSITORY_ROOT / "04-命令与技能/00-Slash-Command通用模块/README.md",
    REPOSITORY_ROOT / "04-命令与技能/01-内置命令/README.md",
    REPOSITORY_ROOT / "04-命令与技能/02-技能命令/README.md",
)
HELP_ROOT = REPOSITORY_ROOT / "04-命令与技能/01-内置命令/Help-Agent使用指南"
HELP_RESULT_FIELDS = {"displayName", "description", "useCases"}
EXPECTED_OPERATION_COUNT = 7
EXPECTED_OPERATIONS = {
    ("POST", "/agents/{agentId}/sessions"),
    ("GET", "/sessions/{sessionId}"),
    ("DELETE", "/sessions/{sessionId}"),
    ("GET", "/sessions/{sessionId}/models"),
    ("POST", "/sessions/{sessionId}"),
    ("GET", "/sessions/{sessionId}/commands"),
    ("POST", "/sessions/{sessionId}/command"),
}
POST_EVENTS = ("POST", "/sessions/{sessionId}/events")
POST_COMMAND = ("POST", "/sessions/{sessionId}/command")
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
    examples = common.get("requestHeaderExamples", [])
    require(len(examples) == 1 and examples[0]["id"] == "language",
            "Shared Header examples must be language-only")
    headers = examples[0]["headers"]
    require(len(headers) == 1 and headers[0]["name"] == "Accept-Language"
            and headers[0]["required"] is False, "Shared defaults must not include credentials")


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
    html_source = build_operation_html(models)
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


def validate_operation_header_examples(operation: dict[str, Any]) -> None:
    validate_request_headers(operation)


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
        validate_operation_header_examples(operation)
        if key in {POST_EVENTS, POST_COMMAND}:
            policy = operation.get("credentialPolicy", {})
            require(policy.get("requestHeadersRequired") is False,
                    f"Execution credential Headers must be optional: {key}")
            require(policy.get("entryRejectsMissingCredentials") is False,
                    f"Execution entry must not reject missing credentials: {key}")
            require(policy.get("clawChecksCredentialCompleteness") is False,
                    f"Claw must not check credential completeness: {key}")
            require(policy.get("mateDecidesCredentialFailure") is True,
                    f"Mate must decide credential failure: {key}")
            require("tool execute" in policy.get("toolExecuteFailure", ""),
                    f"Execution must defer credential failure to tool execute: {key}")
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
    validate_response_reuse(models)


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
        ("POST", "/sessions/{sessionId}"),
    }:
        success = next(response for response in operation["responses"] if response["status"] == "200")
        result = next(body["result"] for body in success["bodies"].values() if isinstance(body, dict))
        require("displayName" in result, f"SessionResource is missing displayName: {key}")
        if key == ("POST", "/sessions/{sessionId}"):
            validate_session_update(operation, codes)
    elif key == ("DELETE", "/sessions/{sessionId}"):
        require(("409", "SESSION_BUSY") in codes, "Delete Session must reject active execution")
    elif key == ("GET", "/sessions/{sessionId}/commands"):
        require("Builtin 与 Skill Command 由用户统一负责设计、实现和集成" in (ROOT.parents[1] / "04-命令与技能/00-Slash-Command通用模块/README.md").read_text(encoding="utf-8"),
                "Command catalog must reflect unified Builtin and Skill ownership")
        validate_catalog_examples(operation)
        require(("503", "AGENT_NOT_AVAILABLE") in codes,
                "Shared GET must reject missing complete Agent cache, not return partial Builtins")
        missing_cache = next(response for response in operation["responses"] if response["status"] == "503")
        require(missing_cache["headers"].get("Retry-After") == "3", "GET cache retry hint differs")
        for response in operation["responses"]:
            if response["status"] == "200":
                commands = response["bodies"]["zh-CN"]["result"]["commands"]
                validate_help_descriptor(next(command for command in commands if command["name"] == "help"))
    elif key == ("POST", "/sessions/{sessionId}/command"):
        require("Builtin 与 Skill Command 由用户统一负责设计、实现和集成" in (ROOT.parents[1] / "04-命令与技能/00-Slash-Command通用模块/README.md").read_text(encoding="utf-8"),
                "Command execution must reflect unified Builtin and Skill ownership")
        for phrase in ("只在内存中保留到本次命令处理", "Mate tool execute",
                       "不写入 Session、事件或日志", "工具发现", "Active Holder"):
            require(phrase in contract_text(operation), f"Missing credential boundary: {phrase}")
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
            ("422", "PLAN_MODE_UNAVAILABLE"),
            ("500", "COMMAND_EXECUTION_FAILED"), ("500", "SESSION_NAME_UPDATE_FAILED"),
            ("503", "MANAGER_UNAVAILABLE"), ("503", "RUNTIME_CAPACITY_EXCEEDED"),
        }:
            require(expected in codes, f"POST Command is missing {expected}")
        successes = [response for response in operation["responses"] if response["status"] == "200"]
        for response in successes:
            skill = response["id"] == "200-skill-message"
            require(response["headers"].get("Content-Type") == ("text/event-stream" if skill else "application/json"),
                    "Skill must use shared SSE; Builtin must retain JSON")
            require(response["headers"].get("Cache-Control") == "no-store", "Missing no-store")
            require(("default" in response["bodies"]) == skill, "response body branch differs")
        require(any(r["id"] == "200-skill-message" for r in successes), "Skill SSE example missing")
        serialized = json.dumps(operation, ensure_ascii=False)
        require("event: command." not in serialized and "event: stream." not in serialized,
                "POST Command must not expose request-scoped SSE lifecycle events")
        validate_help_operation(operation)


def validate_session_update(operation: dict[str, Any], codes: set[tuple[str, str]]) -> None:
    fields = {"displayName", "modelId", "thinking", "mode"}
    request = operation["requestBody"]
    require(len(request["example"]) == 1 and set(request["example"]) <= fields,
            "Primary Session example must match a single-field frontend action")
    schema = request["schema"]
    require(schema["type"] == "object" and schema["minProperties"] == 1
            and schema["additionalProperties"] is False and set(schema["properties"]) == fields,
            "Session update must allow nonempty partial updates with no additional fields")
    require(schema.get("maxProperties", len(fields)) >= len(fields),
            "Session update must allow combined fields, not impose a single-field maximum")
    require(not schema.get("required") and not any("default" in field for field in schema["properties"].values()),
            "Partial update must keep all four fields optional and without defaults")
    require(schema["properties"]["thinking"] == {"type": "boolean"}, "Thinking must remain boolean")
    require(schema["properties"]["mode"] == {"type": "string", "enum": ["plan", "build"]},
            "Mode must use plan/build without a request default")
    examples = [case["value"] for case in request["examples"]]
    require({frozenset({field}) for field in fields} <= {frozenset(case) for case in examples},
            "Every individual field must have a partial-update example")
    require(all(case and set(case) <= fields for case in examples)
            and any(set(case) == fields for case in examples),
            "Partial-update examples must cover the combined four-field request")
    require({"thinking": False} in examples, "Explicit false must not be treated as omission")
    require(any(item.get("name") == "If-Match" and item.get("required") is True
                for item in operation["parameters"]), "Session POST must require If-Match")
    for expected in {
        ("400", "INVALID_SESSION_UPDATE_REQUEST"), ("404", "SESSION_NOT_FOUND"),
        ("409", "SESSION_BUSY"), ("412", "SESSION_VERSION_MISMATCH"),
        ("422", "MODEL_NOT_AVAILABLE"), ("422", "THINKING_NOT_SUPPORTED"),
        ("422", "PLAN_MODE_UNAVAILABLE"), ("428", "IF_MATCH_REQUIRED"),
        ("500", "SESSION_UPDATE_FAILED"), ("503", "MANAGER_UNAVAILABLE"),
    }:
        require(expected in codes, f"Session POST is missing {expected}")
    serialized = json.dumps(operation, ensure_ascii=False)
    for phrase in ("UTF-8", "80", "idle/running", "/name", "名称不写入 Session Entry",
                   "整笔", "显式 null", "重复", "目标模型", "不启动", "未提交"):
        require(phrase in serialized, f"Session update contract is incomplete: {phrase}")
    cases = {case["id"]: case for case in operation["responses"] if case["status"] == "200"}
    require(set(cases) == {"200-updated", "200-unchanged", "200-name-running", "200-model-normalized"},
            "Session update must cover combined, unchanged, running-name and normalization cases")
    result = lambda identity: next(iter(cases[identity]["bodies"].values()))["result"]
    require(result("200-updated") == result("200-unchanged")
            and cases["200-updated"]["headers"]["ETag"] == cases["200-unchanged"]["headers"]["ETag"],
            "Unchanged update must preserve resource and ETag")
    require(result("200-name-running")["state"] == "running", "Name-only update remains available while running")
    require(result("200-updated")["state"] == "idle" and result("200-updated")["mode"] == "plan",
            "Combined execution settings require idle")
    require(result("200-model-normalized")["thinking"] is False, "Preserve omitted-thinking normalization")
    for case in cases.values():
        require(case["headers"].get("Cache-Control") == "no-store" and "ETag" in case["headers"],
                "Session update response must carry a noncached resource and ETag")


def validate_help_descriptor(descriptor: dict[str, Any]) -> None:
    from command_catalog_contract import validate_descriptor
    validate_descriptor(descriptor)
    require(descriptor["name"] == "help" and descriptor["type"] == "builtin"
            and descriptor["description"] == "介绍当前 Agent 的用途和使用场景"
            and descriptor.get("hints", []) == [],
            "Help descriptor must advertise only the no-argument Agent guide")


def validate_help_body(body: dict[str, Any]) -> None:
    require(set(body) == {"resCode", "resMsg", "result"} and body["resCode"] == "0"
            and body["resMsg"] == "success", "Help success ResultBean differs")
    result = body["result"]
    require(isinstance(result, dict) and set(result) == HELP_RESULT_FIELDS,
            "Help must expose exactly three business fields, never commands or internal metadata")
    require(isinstance(result["displayName"], str) and bool(result["displayName"].strip()),
            "Help displayName must be a non-blank Agent name")
    for field in ("description", "useCases"):
        require(isinstance(result[field], list), f"Help {field} must be a non-null array")
        require(all(isinstance(item, str) and bool(item.strip()) and item == item.strip()
                    for item in result[field]), f"Help {field} items must be normalized non-blank strings")


def help_successes(operation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {response["id"]: response for response in operation["responses"]
            if response.get("id", "").startswith("200-help")}


def validate_help_operation(operation: dict[str, Any]) -> None:
    successes = help_successes(operation)
    require(set(successes) == {"200-help", "200-help-empty"},
            "Help must document populated and empty successful responses")
    for response in successes.values():
        for body in response["bodies"].values():
            validate_help_body(body)
    empty = successes["200-help-empty"]["bodies"]["zh-CN"]["result"]
    require(empty["description"] == [] and empty["useCases"] == [], "Help empty response differs")
    populated = successes["200-help"]["bodies"]["zh-CN"]["result"]
    require(bool(populated["description"]) and bool(populated["useCases"]), "Missing populated Help example")
    examples = operation["requestBody"].get("examples", [])
    require(any(example.get("value") == {"name": "help"} for example in examples),
            "POST Command must show the no-argument Help request")
    for phrase in ("Help 只接受空参数", "缺省/null/空白", "非空参数", "INVALID_COMMAND_REQUEST"):
        require(phrase in operation["requestBody"]["description"], f"Missing Help request rule: {phrase}")
    require(("422", "AGENT_NOT_AVAILABLE") in response_codes(operation), "Missing Help cache failure")


def validate_help_projection(model: dict[str, Any], operation: dict[str, Any]) -> None:
    require(model["review"]["questions"] == [], "Confirmed Help must not reopen review choices")
    require("已确认" in model["api"]["visibility"] and "draft" not in model["api"]["version"],
            "Help projection must remain confirmed")
    require(read_design_version() in model["api"]["version"], "Help projection Runtime version is stale")
    view = model["operation"]
    require("authModes" not in view, "Help must not retain a second, unused Header example source")
    require(view["requestHeaderExamples"] == [mode for mode in operation["requestHeaderExamples"]
                                                   if mode["id"] == "builtin"],
            "Help request Header examples and descriptions must match Runtime")
    require((view["method"], view["path"]) == POST_COMMAND, "Help must reuse the Runtime Command path")
    require(view["parameters"] == operation["parameters"], "Help parameters must come from Runtime")
    for field in ("required", "contentType", "description"):
        require(view["requestBody"][field] == operation["requestBody"][field],
                f"Help request rule must come from Runtime: {field}")
    require(view["requestBody"]["example"] == {"name": "help"}, "Help request projection differs")
    source_successes, view_successes = help_successes(operation), help_successes(view)
    require(set(source_successes) == set(view_successes), "Help projection success variants differ")
    for identity, response in source_successes.items():
        for field in ("status", "headers", "bodies", "summary", "tabLabel", "label"):
            require(view_successes[identity][field] == response[field],
                    f"Help projection differs from Runtime: {identity}.{field}")
    source_errors = {response["id"]: response for response in operation["responses"]
                     if response["status"] != "200"}
    for response in view["responses"]:
        if response["status"] == "200":
            continue
        source = source_errors.get(response["id"])
        require(source is not None and response["status"] == source["status"]
                and response["bodies"] == source["bodies"], "Help error projection differs from Runtime")


def validate_help_artifacts(models: list[dict[str, Any]]) -> None:
    require(not (HELP_ROOT / "help-review.json").exists(), "Help must not keep a second JSON source")
    model = load_help_model()
    operation = next(model["operation"] for model in models
                     if model["operation"]["operationKey"] == "ExecuteSessionCommand")
    validate_help_projection(model, operation)
    parser = ContractHtmlParser()
    html_source = (HELP_ROOT / "help-review.html").read_text(encoding="utf-8")
    require(html_source == build_operation_html([model]), "Help HTML must use the shared renderer")
    parser.feed(html_source)
    embedded, _ = parse_generated_models(parser)
    require(embedded == [model], "Help HTML embedded model is stale")
    for attrs, source in parser.scripts:
        if attrs.get("type") != "application/json":
            validate_executable_script(source)
    visible = " ".join(parser.visible_text)
    for example in model["operation"]["requestHeaderExamples"]:
        for header in example["headers"]:
            require(header["value"] in visible and header["description"] in visible,
                    "Help visible Header values or descriptions differ from Runtime")
    for placeholder in ("<JWT>", "<APPKEY>", "<ACCESS_TOKEN>"):
        require(placeholder not in visible, "Help visible HTML still contains obsolete Header placeholders")
    for phrase in ("作用", "name", "help", "description", "useCases", "AGENT_NOT_AVAILABLE", "已确认"):
        require(phrase in visible, f"Help no-script surface is missing {phrase}")
    guide = (HELP_ROOT / "README.md").read_text(encoding="utf-8")
    for phrase in ("显式刷新", "toIdentity", "toRuntime", "进程重启", "schemaVersion", "Agent 级锁"):
        require(phrase in guide, f"Help cache implementation acceptance is missing {phrase}")


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
        if operation.get("operationKey") in {"UpdateSession", "ExecuteSessionCommand"}:
            require("requestHeaderExamples" in operation, "Body POST needs scoped Header examples")
        else:
            require("requestHeaderExamples" not in operation,
                    f"Shared language Header duplicated in {operation_path.name}")
        references = [item.get("$ref") for item in operation["responses"] if isinstance(item, dict)]
        require("responses.unauthenticated" not in references,
                f"Runtime-local authentication error found in {operation_path.name}")
        require("responses.authCredentialConflict" not in references,
                f"Runtime-local credential conflict found in {operation_path.name}")


def diagram_sources() -> list[Path]:
    sources = sorted((ROOT / "设计图").glob("*/diagram.puml"))
    sources.extend(path.parent / "设计图/diagram.puml" for path in SLASH_DESIGN_PATHS)
    sources.append(HELP_ROOT / "diagram.puml")
    require(sources, "No topic PlantUML sources found")
    require(not (ROOT / "diagram.puml").exists(), "Legacy aggregate diagram.puml still exists")
    return sources


def diagram_names(source: Path) -> list[str]:
    content = source.read_text(encoding="ascii")
    names = re.findall(r"^@startuml\s+([A-Za-z0-9_]+)\s*$", content, re.MULTILINE)
    require(names, f"No named diagrams in {source.relative_to(REPOSITORY_ROOT)}")
    return names


def validate_diagram_inventory(sources: list[Path]) -> None:
    for source in sources:
        require(source.read_bytes().isascii(), f"Non-ASCII PlantUML: {source.relative_to(REPOSITORY_ROOT)}")
        expected = {f"{name}.svg" for name in diagram_names(source)}
        actual = {path.name for path in source.parent.glob("*.svg")}
        require(actual == expected, f"SVG inventory differs in {source.parent.relative_to(REPOSITORY_ROOT)}")
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
    for markdown_path in REPOSITORY_ROOT.rglob("*.md"):
        content = markdown_path.read_text(encoding="utf-8")
        require("```mermaid" not in content, f"Mermaid is forbidden: {markdown_path.relative_to(REPOSITORY_ROOT)}")
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
    ownership_paths = (*SLASH_DESIGN_PATHS, DESIGN_PATH, ROOT / "README.md",
                       REPOSITORY_ROOT / "README.md", REPOSITORY_ROOT / "04-命令与技能/README.md")
    retired_ownership = ("Skill Command 由其他同事", "Skill 执行由其他同事", "Skill 由其他同事",
                         "Skill 由同事", "真实 Skill 执行由同事", "Skill 执行由同事",
                         "同事并行实现执行定义", "真实执行定义由同事", "Skill 开发线",
                         "Skill 执行开发线", "本会话只负责七个 Builtin")
    for path in ownership_paths:
        active = re.split(r"^## (?:\d+\. )?版本历史", path.read_text(encoding="utf-8"),
                          maxsplit=1, flags=re.MULTILINE)[0]
        for wording in retired_ownership:
            require(wording not in active,
                    f"Superseded Command ownership in {path.relative_to(REPOSITORY_ROOT)}: {wording}")
    for path in SLASH_DESIGN_PATHS:
        source = (path.parent / "设计图/diagram.puml").read_text(encoding="ascii")
        require("parallel work" not in source, "Command diagrams must reflect unified implementation ownership")
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


def validate_control_retirement(models: list[dict[str, Any]]) -> None:
    retired = {"appendSteer", "appendFollowUp", "abortSession"}
    paths = {f"/sessions/{{sessionId}}/{name}" for name in ("steers", "follow-ups", "abort")}
    for model in models:
        operation = model["operation"]
        require(operation["operationKey"] not in retired and operation["path"] not in paths,
                "Retired standalone control operation must not re-enter the active catalog")
    html_text = HTML_PATH.read_text(encoding="utf-8")
    require(not any(path in html_text for path in paths), "Retired control path found in active review HTML")
    future = (ROOT / "chat-follow-up-future-design.md").read_text(encoding="utf-8")
    for phrase in ("本期不支持", "启用另行评审", "待实现", "M1 未完成前拒绝", "内存凭据"):
        require(phrase in future, f"Future FollowUp must retain the disabled boundary: {phrase}")


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
    validate_help_artifacts(models)
    sources = diagram_sources()
    validate_diagram_inventory(sources)
    selected = select_diagrams(sources, args.full)
    validate_rendered_diagrams(selected)
    validate_markdown_links()
    validate_command_wording(models)
    validate_removed_contract()
    validate_control_retirement(models)
    run(["git", "diff", "--check"], cwd=REPOSITORY_ROOT)
    mode = "full" if args.full else "fast"
    print(f"Retained contract validation passed: {len(models)} operations, {len(selected)} diagram topics ({mode}); full inventory: validate-chat-api.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

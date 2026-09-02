#!/usr/bin/env python3
"""Validate the confirmed mate-service General Chat events artifacts."""

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

from render_chat_events_v1 import MODELS, OUTPUT, ROOT, renderer_path


REPOSITORY_ROOT = ROOT.parents[1]
DESIGN = ROOT / "README.md"
PUML = ROOT / "设计图" / "diagram.puml"
OPENAPI = ROOT / "chat-events-v1.openapi.yaml"
EVENT_ID = re.compile(r"^[0-9a-f]{32}$")
CREATED_AT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
LOWER_CAMEL = re.compile(r"^[a-z][A-Za-z0-9]*$")
USER_TYPES = {"user.message", "user.interrupt", "user.tool_confirmation"}
STREAM_TYPES = {
    "agent.message",
    "agent.thinking",
    "agent.tool_call",
    "agent.tool_result",
    "chat.status_idle",
}
HISTORY_TYPES = USER_TYPES | STREAM_TYPES
IDLE_REASONS = {"done", "terminated", "failed", "confirming"}


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


def load_openapi() -> dict[str, Any]:
    require(shutil.which("ruby") is not None, "ruby is required for YAML validation")
    program = (
        "document = YAML.safe_load(File.read(ARGV[0]), permitted_classes: [], aliases: false); "
        "puts JSON.generate(document)"
    )
    result = subprocess.run(
        ["ruby", "-ryaml", "-rjson", "-e", program, str(OPENAPI)],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    document = json.loads(result.stdout)
    require(isinstance(document, dict), "OpenAPI root must be an object")
    return document


def validate_lower_camel(value: Any, context: str) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            require(LOWER_CAMEL.fullmatch(key) is not None, f"Non-lowerCamel field in {context}: {key}")
            validate_lower_camel(nested, context)
    elif isinstance(value, list):
        for item in value:
            validate_lower_camel(item, context)


def response(model: dict[str, Any], response_id: str) -> dict[str, Any]:
    return next(item for item in model["operation"]["responses"] if item["id"] == response_id)


def validate_auth(operation: dict[str, Any]) -> None:
    modes = operation["authModes"]
    require([mode["id"] for mode in modes] == ["jwt", "appkey"], "Unexpected authentication modes")
    require([mode["preferred"] for mode in modes] == [True, False], "JWT must be preferred")
    jwt = {header["name"] for header in modes[0]["headers"]}
    appkey = {header["name"] for header in modes[1]["headers"]}
    require(jwt == {"X-HW-ID", "access-token", "Authorization"}, "JWT headers changed")
    require(appkey == {"X-HW-ID", "access-token", "X-HW-APPKEY"}, "APPKEY headers changed")


def validate_common_model(model: dict[str, Any]) -> None:
    require(model["api"]["version"] == "1.0.0", "Unexpected contract version")
    require(model["api"]["basePath"] == "/mate-service/v1", "Unexpected base path")
    require("已确认" in model["api"]["visibility"], "Contract must be confirmed")
    require(model["review"]["questions"] == [], "Confirmed contract must not contain review choices")
    validate_auth(model["operation"])
    for item in model["operation"]["responses"]:
        require(item["headers"].get("Cache-Control") == "no-store", f"Missing no-store: {item['id']}")
        for body in item["bodies"].values():
            if isinstance(body, dict):
                validate_lower_camel(body, item["id"])
                require("resCode" in body and "resMsg" in body, f"Invalid ResultBean: {item['id']}")
                if body["resCode"] != "0":
                    require(set(body) == {"resCode", "resMsg"}, f"Error body leaks fields: {item['id']}")


def validate_event_id(value: Any, context: str) -> None:
    require(isinstance(value, str) and EVENT_ID.fullmatch(value) is not None, f"Invalid eventId: {context}")


def validate_created_at(value: Any, context: str) -> None:
    require(isinstance(value, str) and CREATED_AT.fullmatch(value) is not None,
            f"Invalid createdAt: {context}")


def validate_submit(model: dict[str, Any]) -> None:
    operation = model["operation"]
    require((operation["method"], operation["path"]) == ("POST", "/chats/{chatId}/events"),
            "Submit operation changed")
    example = operation["requestBody"]["example"]
    require(set(example) == {"event"}, "Submit body must contain only event")
    event = example["event"]
    require(event["type"] == "user.message", "Submit example must be user.message")
    require([item["type"] for item in event["content"]] == ["text", "file"],
            "Submit example must show text then file")
    validate_event_id(event["content"][1]["fileId"], "submit fileId")
    accepted = response(model, "200-accepted")["bodies"]["default"]
    require(accepted["resCode"] == "0" and accepted["resMsg"] == "success", "Submit ResultBean changed")
    require(set(accepted["result"]) == {"eventId", "createdAt"}, "Submit receipt contains redundant fields")
    validate_event_id(accepted["result"]["eventId"], "submit receipt")
    validate_created_at(accepted["result"]["createdAt"], "submit receipt")
    codes = {
        body["resCode"]
        for item in operation["responses"]
        for body in item["bodies"].values()
        if isinstance(body, dict) and body["resCode"] != "0"
    }
    required = {
        "CHAT_ID_INVALID",
        "CHAT_EVENT_INVALID",
        "CHAT_EVENT_TYPE_INVALID",
        "UNAUTHENTICATED",
        "CHAT_ACCESS_DENIED",
        "CHAT_NOT_FOUND",
        "CHAT_BUSY",
        "CHAT_NOT_RUNNING",
        "TOOL_CONFIRMATION_NOT_PENDING",
        "CHAT_RUNTIME_UNAVAILABLE",
    }
    require(required <= codes, f"Missing submit errors: {sorted(required - codes)}")


def parse_sse(stream: str) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for block in stream.strip().split("\n\n"):
        lines = block.splitlines()
        if all(line.startswith(":") for line in lines):
            require(lines == [": ping"], f"Unexpected SSE comment: {block}")
            continue
        require(len(lines) == 1 and lines[0].startswith("data: "), f"Frame is not data-only: {block}")
        require(not lines[0].startswith("event:") and not lines[0].startswith("id:"), "Named SSE field leaked")
        payload = json.loads(lines[0].removeprefix("data: "))
        require(isinstance(payload, dict), "SSE data must be an object")
        payloads.append(payload)
    return payloads


def validate_stream_payload(payload: dict[str, Any]) -> None:
    validate_lower_camel(payload, "SSE")
    require(payload["type"] in STREAM_TYPES, f"Unsupported SSE type: {payload['type']}")
    validate_event_id(payload["eventId"], payload["type"])
    require("eventSeq" not in payload and "sessionId" not in payload, "Internal identity leaked to SSE")
    if payload["type"] in {"agent.message", "agent.thinking"}:
        require(payload["phase"] in {"delta", "completed"}, "Invalid text phase")
        require(isinstance(payload["content"], str) and payload["content"] != "", "Text content must be non-empty")
        if payload["phase"] == "delta":
            require(set(payload) == {"eventId", "type", "phase", "content"},
                    "Delta contains fields outside the flat contract")
        else:
            require(set(payload) == {"eventId", "type", "phase", "createdAt", "content"},
                    "Completed text shape changed")
            validate_created_at(payload["createdAt"], payload["type"])
    else:
        validate_created_at(payload["createdAt"], payload["type"])
    if payload["type"] == "agent.tool_call":
        require(set(payload) == {
            "eventId", "type", "createdAt", "toolName", "arguments", "requiresConfirmation"
        }, "Tool Call shape changed")
        require(isinstance(payload["arguments"], dict), "Tool arguments must be an object")
        require(isinstance(payload["requiresConfirmation"], bool), "requiresConfirmation must be boolean")
    if payload["type"] == "agent.tool_result":
        allowed = {"eventId", "type", "createdAt", "toolCallId", "content", "isError", "errorCode"}
        require(set(payload) <= allowed and {"eventId", "type", "createdAt", "toolCallId", "content", "isError"} <= set(payload),
                "Tool Result shape changed")
        validate_event_id(payload["toolCallId"], "tool result toolCallId")
        require(isinstance(payload["content"], str) and isinstance(payload["isError"], bool),
                "Invalid Tool Result values")
        require("errorCode" not in payload or payload["isError"], "errorCode is only allowed for errors")
    if payload["type"] == "chat.status_idle":
        require(set(payload) == {"eventId", "type", "createdAt", "reason"}, "Idle shape changed")
        require(payload["reason"] in IDLE_REASONS, "Invalid idle reason")


def validate_stream(model: dict[str, Any]) -> None:
    operation = model["operation"]
    require((operation["method"], operation["path"]) == ("GET", "/chats/{chatId}/events/stream"),
            "Stream operation changed")
    require(operation["requestBody"]["required"] is False, "Stream GET must not have a body")
    stream = response(model, "200-live-stream")["bodies"]["default"]
    require("event: " not in stream and "\nid: " not in stream, "SSE event/id fields are forbidden")
    payloads = parse_sse(stream)
    require({item["type"] for item in payloads} == STREAM_TYPES, "SSE sample must cover all five types")
    for payload in payloads:
        validate_stream_payload(payload)
    for event_type in ("agent.message", "agent.thinking"):
        pair = [item for item in payloads if item["type"] == event_type]
        require([item["phase"] for item in pair] == ["delta", "completed"], f"{event_type} phase order changed")
        require(pair[0]["eventId"] == pair[1]["eventId"], f"{event_type} must reuse eventId")
    require("stream.error" not in stream and "stream.end" not in stream, "Terminal stream events are forbidden")


def validate_history_event(event: dict[str, Any]) -> None:
    validate_lower_camel(event, "history")
    require(event["type"] in HISTORY_TYPES, f"Unsupported history type: {event['type']}")
    validate_event_id(event["eventId"], event["type"])
    validate_created_at(event["createdAt"], event["type"])
    require("eventSeq" not in event and "sessionId" not in event, "Internal identity leaked to history")
    if event["type"] in {"agent.message", "agent.thinking"}:
        require(event["phase"] == "completed", "History must contain completed text only")
    if event["type"] == "agent.tool_call":
        require("toolCallId" not in event, "Tool Call must use eventId directly")
        require(isinstance(event["arguments"], dict), "Tool Call arguments must be an object")
    if event["type"] == "agent.tool_result":
        validate_event_id(event["toolCallId"], "history Tool Result")
        require("errorCode" not in event or event["isError"], "History errorCode is only allowed for errors")
    if event["type"] == "user.tool_confirmation":
        validate_event_id(event["toolCallId"], "history Tool Confirmation")
        require(event["result"] in {"allow", "deny"}, "Invalid confirmation result")
        require(("denyMessage" in event) <= (event["result"] == "deny"), "denyMessage present for allow")
    if event["type"] == "chat.status_idle":
        require(event["reason"] in IDLE_REASONS, "Invalid history idle reason")


def validate_history(model: dict[str, Any]) -> None:
    operation = model["operation"]
    require((operation["method"], operation["path"]) == ("GET", "/chats/{chatId}/events"),
            "History operation changed")
    query_names = [item["name"] for item in operation["parameters"] if item["in"] == "query"]
    require(query_names == ["createdAtGte", "limit", "types", "page"], "History query parameters changed")
    success = response(model, "200-history-page")["bodies"]["default"]
    result = success["result"]
    require(set(result) == {"events", "nextPage"}, "History success example changed")
    events = result["events"]
    require({event["type"] for event in events} == HISTORY_TYPES, "History sample must cover all eight types")
    for event in events:
        validate_history_event(event)
    require([event["createdAt"] for event in events] == sorted(event["createdAt"] for event in events),
            "History sample is not ordered by createdAt")
    require(isinstance(result["nextPage"], str) and result["nextPage"], "nextPage must be opaque and non-empty")
    codes = {
        body["resCode"]
        for item in operation["responses"]
        for body in item["bodies"].values()
        if isinstance(body, dict) and body["resCode"] != "0"
    }
    required = {
        "CHAT_ID_INVALID",
        "CHAT_EVENT_CREATED_AT_GTE_INVALID",
        "CHAT_EVENT_LIMIT_INVALID",
        "CHAT_EVENT_TYPES_INVALID",
        "CHAT_EVENT_PAGE_CONFLICT",
        "CHAT_EVENT_PAGE_INVALID",
        "UNAUTHENTICATED",
        "CHAT_ACCESS_DENIED",
        "CHAT_NOT_FOUND",
    }
    require(required <= codes, f"Missing history errors: {sorted(required - codes)}")


def validate_openapi(models: list[dict[str, Any]]) -> None:
    require(OPENAPI.is_file(), "OpenAPI document is missing")
    spec = load_openapi()
    require(spec["openapi"] == "3.1.0", "OpenAPI version must be 3.1.0")
    require(spec["info"]["version"] == models[0]["api"]["version"], "OpenAPI contract version drifted")
    require(spec["servers"] == [{
        "url": "/mate-service/v1",
        "description": "相对于公司网关的业务基础路径",
    }], "OpenAPI server base path changed")
    validate_openapi_security(spec)
    validate_openapi_submit(spec, models[0])
    validate_openapi_stream(spec)
    validate_openapi_history(spec, models[2])
    validate_openapi_errors(spec)
    source = OPENAPI.read_text(encoding="utf-8")
    require("traceparent" not in source.lower(), "traceparent is forbidden")
    require("eventSeq" not in source, "OpenAPI must not expose eventSeq")
    require("JWT 优先" in source and "不回退" in source, "Confirmed authentication precedence is missing")


def validate_openapi_security(spec: dict[str, Any]) -> None:
    requirements = spec["security"]
    require(len(requirements) == 2, "OpenAPI must expose two authentication alternatives")
    require(set(requirements[0]) == {"XHwId", "AccessToken", "BearerAuth"},
            "JWT security requirement changed")
    require(set(requirements[1]) == {"XHwId", "AccessToken", "AppKeyAuth"},
            "APPKEY security requirement changed")
    require(all(value == [] for item in requirements for value in item.values()),
            "Security requirement scopes must be empty")
    schemes = spec["components"]["securitySchemes"]
    require(schemes["XHwId"]["name"] == "X-HW-ID", "X-HW-ID security scheme changed")
    require(schemes["AccessToken"]["name"] == "access-token", "access-token security scheme changed")
    require(schemes["AppKeyAuth"]["name"] == "X-HW-APPKEY", "APPKEY security scheme changed")
    require(schemes["BearerAuth"]["scheme"] == "bearer", "Bearer security scheme changed")


def validate_openapi_submit(spec: dict[str, Any], model: dict[str, Any]) -> None:
    operation = spec["paths"]["/chats/{chatId}/events"]["post"]
    require(operation["operationId"] == "submitChatEvent", "Submit operationId changed")
    media = operation["requestBody"]["content"]["application/json"]
    require(media["schema"]["$ref"].endswith("/SubmitChatEventRequest"), "Submit request wrapper changed")
    examples = media["examples"]
    require(set(examples) == {
        "userMessage",
        "userInterrupt",
        "toolConfirmationAllow",
        "toolConfirmationDeny",
    }, "Submit named examples changed")
    values = {name: item["value"]["event"] for name, item in examples.items()}
    require(values["userMessage"]["type"] == "user.message", "Message example changed")
    require(values["userInterrupt"] == {"type": "user.interrupt"}, "Interrupt example changed")
    require(values["toolConfirmationAllow"]["result"] == "allow"
            and "denyMessage" not in values["toolConfirmationAllow"], "Allow example changed")
    require(values["toolConfirmationDeny"]["result"] == "deny"
            and values["toolConfirmationDeny"]["denyMessage"], "Deny example changed")
    user_event = spec["components"]["schemas"]["UserEvent"]
    require(set(user_event["discriminator"]["mapping"]) == USER_TYPES, "UserEvent discriminator changed")
    require(len(user_event["oneOf"]) == 3, "UserEvent must contain three alternatives")
    message = spec["components"]["schemas"]["UserMessageRequestEvent"]["properties"]["content"]
    require((message["minItems"], message["maxItems"], message["uniqueItems"]) == (1, 5, True),
            "Message content array constraints changed")
    confirmation = spec["components"]["schemas"]["UserToolConfirmationRequestEvent"]
    require(set(confirmation["required"]) == {"type", "toolCallId", "result"},
            "Confirmation required fields changed")
    success = operation["responses"]["200"]["content"]["application/json"]["example"]
    model_success = response(model, "200-accepted")["bodies"]["default"]
    require(success == model_success, "Submit success example drifted from review model")


def validate_openapi_stream(spec: dict[str, Any]) -> None:
    operation = spec["paths"]["/chats/{chatId}/events/stream"]["get"]
    require(operation["operationId"] == "streamChatEvents", "Stream operationId changed")
    success = operation["responses"]["200"]
    media = success["content"]["text/event-stream"]
    require(media["schema"]["type"] == "string", "SSE wire schema must remain a string")
    payloads = parse_sse(media["example"])
    require({item["type"] for item in payloads} == STREAM_TYPES,
            "OpenAPI SSE example must cover all five stream types")
    for payload in payloads:
        validate_stream_payload(payload)
    data_schema = success["x-sse-data-schema"]
    require(len(data_schema["oneOf"]) == 7, "SSE data schema must contain seven phase variants")
    require("event: " not in media["example"] and "\nid: " not in media["example"],
            "OpenAPI SSE example must be data-only")


def validate_openapi_history(spec: dict[str, Any], model: dict[str, Any]) -> None:
    operation = spec["paths"]["/chats/{chatId}/events"]["get"]
    require(operation["operationId"] == "listChatEvents", "History operationId changed")
    refs = [item["$ref"].rsplit("/", 1)[-1] for item in operation["parameters"]]
    require(refs == ["ChatId", "CreatedAtGte", "Limit", "Types", "Page", "AcceptLanguage"],
            "OpenAPI history parameters changed")
    types = spec["components"]["schemas"]["HistoryEventType"]["enum"]
    require(set(types) == HISTORY_TYPES and len(types) == len(HISTORY_TYPES),
            "OpenAPI history types changed")
    history = spec["components"]["schemas"]["HistoryEvent"]
    require(len(history["oneOf"]) == 8, "HistoryEvent must contain eight alternatives")
    require(set(history["discriminator"]["mapping"]) == HISTORY_TYPES,
            "HistoryEvent discriminator changed")
    next_page = operation["responses"]["200"]["content"]["application/json"]["example"]["result"]["nextPage"]
    model_page = response(model, "200-history-page")["bodies"]["default"]["result"]["nextPage"]
    require(next_page == model_page, "Opaque page example drifted from review model")
    require(re.fullmatch(r"pg_[A-Za-z0-9]+", next_page) is not None,
            "Page example must not visibly encode a timestamp, sequence, or offset")


def validate_openapi_errors(spec: dict[str, Any]) -> None:
    def check_response(raw_response: dict[str, Any], context: str) -> None:
        if "$ref" in raw_response:
            return
        content = raw_response.get("content", {}).get("application/json", {})
        examples = list(content.get("examples", {}).values())
        if "example" in content:
            examples.append({"value": content["example"]})
        for item in examples:
            value = item["value"]
            if isinstance(value, dict) and value.get("resCode") != "0":
                require(set(value) == {"resCode", "resMsg"}, f"OpenAPI error leaks fields: {context}")

    for path, path_item in spec["paths"].items():
        for method, operation in path_item.items():
            if method not in {"get", "post"}:
                continue
            for status, raw_response in operation["responses"].items():
                if status != "200":
                    check_response(raw_response, f"{method.upper()} {path} {status}")
    for name, raw_response in spec["components"]["responses"].items():
        check_response(raw_response, f"component response {name}")
    error = spec["components"]["schemas"]["ErrorResponse"]
    require(error["additionalProperties"] is False
            and set(error["required"]) == {"resCode", "resMsg"}, "ErrorResponse shape changed")


def validate_html() -> None:
    require(OUTPUT.is_file(), "Generated review HTML is missing")
    with tempfile.TemporaryDirectory() as directory:
        candidate = Path(directory) / OUTPUT.name
        command = ["python3", str(renderer_path()), str(MODELS[0]), str(candidate), "--standalone"]
        for model in MODELS[1:]:
            command.extend(["--include", str(model)])
        run(command)
        require(candidate.read_bytes() == OUTPUT.read_bytes(), "Generated review HTML is stale")
    source = OUTPUT.read_text(encoding="utf-8")
    require("@media" in source, "Responsive review styles are missing")
    for path in ("/chats/{chatId}/events", "/chats/{chatId}/events/stream"):
        require(path in source, f"Operation missing from review HTML: {path}")
    parser = ScriptParser()
    parser.feed(source)
    executable = [script for attrs, script in parser.scripts if attrs.get("type") != "application/json"]
    require(len(executable) == len(MODELS), "Expected one executable script per operation")
    require(shutil.which("node") is not None, "node is required for JavaScript syntax validation")
    with tempfile.TemporaryDirectory() as directory:
        for index, source_code in enumerate(executable):
            script = Path(directory) / f"review-{index}.js"
            script.write_text(source_code, encoding="utf-8")
            run(["node", "--check", str(script)])


def diagram_names() -> list[str]:
    source = PUML.read_text(encoding="ascii")
    names = re.findall(r"^@startuml\s+([A-Za-z0-9_]+)\s*$", source, re.MULTILINE)
    require(names == ["public_chat_event_boundary", "public_chat_event_recovery"],
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
            require((temporary.parent / f"{name}.svg").read_bytes()
                    == (PUML.parent / f"{name}.svg").read_bytes(),
                    f"Generated SVG is stale: {name}.svg")
    require(not (PUML.parent / "public_chat_event_projection.svg").exists(),
            "Superseded projection diagram still exists")


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
    require(len(MODELS) == 3 and all(path.is_file() for path in MODELS), "Three models are required")
    models = [json.loads(path.read_text(encoding="utf-8")) for path in MODELS]
    for model in models:
        validate_common_model(model)
    validate_submit(models[0])
    validate_stream(models[1])
    validate_history(models[2])
    validate_openapi(models)
    validate_html()
    validate_diagrams()
    validate_markdown()
    run(["git", "diff", "--check"], REPOSITORY_ROOT)
    print("All mate-service Chat events design validations passed.")


if __name__ == "__main__":
    main()

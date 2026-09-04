#!/usr/bin/env python3
"""Validate the confirmed POST and current Session stream proposal."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
COMMON_PATH = ROOT / "接口契约-v2" / "common.json"
MODEL_PATH = ROOT / "接口契约-v2" / "操作" / "01-submit-session-event.json"
STREAM_PATH = ROOT / "接口契约-v2" / "操作" / "02-stream-session-events.json"
USER_EVENT_TYPES = {"user.message", "user.interrupt", "user.tool_confirmation"}
STREAM_TYPES = {"assistant.message", "assistant.thinking", "tool.call", "tool.result", "session.status.idle"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_public_payload(value: object) -> None:
    if isinstance(value, dict):
        require(
            not {"entryId", "entrySeq", "eventSeq", "runId", "executionId"}.intersection(value),
            "v2 public payload must not expose internal identifiers or sequences",
        )
        for child in value.values():
            validate_public_payload(child)
    elif isinstance(value, list):
        for child in value:
            validate_public_payload(child)


def validate_success_events(operation: dict) -> None:
    event_types = set()
    for response in operation["responses"]:
        for body in response["bodies"].values():
            validate_public_payload(body)
            if response["status"] != "200":
                continue
            event = body["result"]["event"]
            event_id = event.get("eventId")
            require(
                isinstance(event_id, str) and bool(event_id.strip()),
                "each v2 success event must have a non-empty eventId",
            )
            event_types.add(event["type"])
    require(event_types == USER_EVENT_TYPES, "v2 success examples must cover all three user event types")


def validate_access_token_rule(operation: dict) -> None:
    modes = operation["requestHeaderExamples"]
    require(
        len(modes) == 2 and {mode["id"] for mode in modes} == {"jwt", "appkey"},
        "v2 POST must retain both Header modes",
    )
    for mode in modes:
        tokens = [header for header in mode["headers"] if header["name"] == "access-token"]
        require(len(tokens) == 1, f"{mode['id']} must contain exactly one access-token Header")
        token = tokens[0]
        require(token.get("required") is True, f"{mode['id']} must require access-token")
        require(token["value"] == "opaque-access-token", "confirmed access-token example must be preserved")
        require(
            "三种用户事件均必须携带" in token["description"],
            f"{mode['id']} must state that all three user event types require access-token",
        )


def validate_event_ordering_rule(review: dict) -> None:
    require("顺序规则已确认" in review["status"], "review must preserve the confirmed ordering decision")
    for rule in (
        "先统一检查事件依赖、确定处理顺序",
        "同一事务内分配内部序号并写入",
        "前置事件未提交时，依赖它的事件不得先进入权威历史",
        "ListEvents 按已提交的内部顺序返回",
        "客户端保持数组顺序，不按 createdAt 重排",
        "不公开 entrySeq",
    ):
        require(rule in review["notice"], f"review must retain the ordering rule: {rule}")


def validate_stream_frame(event: dict) -> None:
    validate_public_payload(event)
    require(event.get("type") in STREAM_TYPES, "unexpected candidate stream event type")
    require(isinstance(event.get("eventId"), str) and bool(event["eventId"]), "stream eventId is required")
    if event["type"] in {"assistant.message", "assistant.thinking"}:
        require(event.get("phase") in {"delta", "completed"}, "text event phase is required")
        require(isinstance(event.get("content"), str), "text content must be a string")
    if event.get("phase") == "delta":
        require("createdAt" not in event and bool(event["content"]), "delta cannot be durable or empty")
    else:
        require(isinstance(event.get("createdAt"), str), "complete event must include createdAt")
    if event["type"] in {"tool.call", "tool.result"}:
        require(bool(event.get("toolCallId")), "toolCallId is required independently of eventId")
    if event["type"] == "session.status.idle":
        require(event.get("reason") in {"done", "terminated", "failed", "confirming"}, "invalid idle reason")


def validate_stream_model(model: dict) -> None:
    operation = model["operation"]
    require(operation["method"] == "GET", "second operation must be GET")
    require(operation["path"] == "/sessions/{sessionId}/events/stream", "unexpected stream path")
    body = operation["requestBody"]
    require(body["required"] is False and body["contentType"] is None and body["example"] is None,
            "stream request must not have a body")
    all_types = set()
    for response in operation["responses"]:
        if response["status"] != "200":
            for error in response["bodies"].values():
                require(set(error) == {"resCode", "resMsg"}, "pre-stream errors must not include result")
            continue
        require(response["headers"]["Content-Type"] == "text/event-stream", "stream media type must be SSE")
        require(response["headers"]["Cache-Control"] == "no-store", "live content must not be cached")
        for stream in response["bodies"].values():
            require(isinstance(stream, str) and stream.startswith(": connected\n\n"), "missing readiness comment")
            completed = set()
            for frame in stream.strip().split("\n\n"):
                if frame.startswith(":"):
                    require(frame in {": connected", ": ping"}, "unexpected stream comment")
                    continue
                require(frame.startswith("data: ") and "\n" not in frame, "business frame must be data-only JSON")
                event = json.loads(frame[6:])
                validate_stream_frame(event)
                require(event["eventId"] not in completed, "completed must be the last frame for an eventId")
                if event.get("phase") != "delta":
                    completed.add(event["eventId"])
                all_types.add(event["type"])
    require(all_types == STREAM_TYPES, "stream examples must cover the five candidate basic types")
    questions = model["review"]["questions"]
    require([q["id"] for q in questions] == ["S1-frame-format", "S2-event-projection", "S3-user-events", "S4-read-access-token"],
            "only second-operation questions may be open")
    require("第二个接口评审中" in model["review"]["status"], "stream proposal must not be marked confirmed")
    for question in questions:
        require(sum(bool(option.get("selected")) for option in question["options"]) == 1,
                f"{question['id']} must have exactly one recommended selection")


def validate_review_pages() -> None:
    spec = importlib.util.spec_from_file_location("runtime_contract_validator", ROOT / "validate-chat-http-v1.py")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    for filename, expected_key, question_count in (
        ("chat-events-v2-review.html", "streamSessionEvents", 4),
        ("chat-events-v2-confirmed.html", "submitSessionEvent", 0),
    ):
        source = (ROOT / filename).read_text(encoding="utf-8")
        parser = validator.ContractHtmlParser()
        parser.feed(source)
        models, scripts = validator.parse_generated_models(parser)
        require(len(models) == parser.static_review_count == len(scripts) == 1, "page must show exactly one operation")
        require(models[0]["operation"]["operationKey"] == expected_key, "wrong operation on review page")
        require(len(models[0]["review"]["questions"]) == question_count, "stale decision form on page")
        validator.validate_executable_script(scripts[0])
        visible = " ".join(parser.visible_text)
        for heading in ("作用", "调用上下文 Header", "参数与请求体", "响应"):
            require(heading in visible, f"no-JavaScript page missing {heading}")
        require("data-label" in source and "max-width: 680px" in source, "responsive field rows missing")


def main() -> int:
    try:
        common = json.loads(COMMON_PATH.read_text(encoding="utf-8"))
        model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
        stream_model = json.loads(STREAM_PATH.read_text(encoding="utf-8"))
        operation = model["operation"]
        review = model["review"]
        require(operation["method"] == "POST", "first v2 operation must be POST")
        require(operation["path"] == "/sessions/{sessionId}/events", "unexpected v2 POST path")
        require("text/event-stream" not in json.dumps(operation, ensure_ascii=False), "v2 POST must not return SSE")
        examples = operation["requestBody"]["examples"]
        event_types = {example["value"]["event"]["type"] for example in examples}
        require(
            event_types == USER_EVENT_TYPES,
            "v2 POST examples must cover all proposed user event types",
        )
        for example in examples:
            validate_public_payload(example["value"])
        validate_success_events(operation)
        validate_access_token_rule(operation)
        validate_event_ordering_rule(review)
        validate_stream_model(stream_model)
        require(common["reviewState"] == {
            "currentOperation": "streamSessionEvents", "confirmedOperations": ["submitSessionEvent"]
        }, "review must advance from confirmed POST to GET stream")
        header_sets = [
            ("common", common["requestHeaderExamples"]),
            ("submitSessionEvent", operation["requestHeaderExamples"]),
            ("streamSessionEvents", stream_model["operation"]["requestHeaderExamples"]),
        ]
        expected_x_hw_id_values = {"jwt": "credential-jwt", "appkey": "credential-appkey"}
        for owner, modes in header_sets:
            for mode in modes:
                require(
                    all("<" not in header["value"] and ">" not in header["value"] for header in mode["headers"]),
                    f"{owner} {mode['id']} must use concrete non-production header examples",
                )
                x_hw_id = next(header for header in mode["headers"] if header["name"] == "X-HW-ID")
                require(
                    x_hw_id["value"] == expected_x_hw_id_values[mode["id"]],
                    f"{owner} {mode['id']} must use the concrete user credential ID example",
                )
                require(
                    "用户凭据 ID" in x_hw_id["description"]
                    and "不是公司、服务或应用标识" in x_hw_id["description"],
                    f"{owner} {mode['id']} must define X-HW-ID as a user credential ID",
                )
        require("瞬态" not in json.dumps(model, ensure_ascii=False), "v2 POST must describe credential handling plainly")
        require(
            "Header 示例与处理说明已确认" in review["status"],
            "review status must preserve the confirmed Header examples and handling description",
        )
        require("eventId 已确认" in review["status"], "review status must preserve the confirmed eventId decision")
        require(
            "access-token 必填规则已确认" in review["status"]
            and "三种用户事件均必须携带 access-token" in review["notice"],
            "review must preserve the confirmed access-token requiredness decision",
        )
        require(
            review["questions"] == [] and "POST 接口已确认" in review["status"],
            "confirmed POST must not retain Q1/Q2/Q3/Q4 decision forms",
        )
        subprocess.run([sys.executable, str(ROOT / "render_chat_events_v2.py"), "--check"], check=True)
        validate_review_pages()
    except (KeyError, OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"error: {error}")
        return 2
    print("Session Events v2 review snapshot is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

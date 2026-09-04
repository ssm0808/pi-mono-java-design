#!/usr/bin/env python3
"""Validate the current one-operation Session Events v2 review snapshot."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
COMMON_PATH = ROOT / "接口契约-v2" / "common.json"
MODEL_PATH = ROOT / "接口契约-v2" / "操作" / "01-submit-session-event.json"
USER_EVENT_TYPES = {"user.message", "user.interrupt", "user.tool_confirmation"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_public_payload(value: object) -> None:
    if isinstance(value, dict):
        require(
            not {"entryId", "entrySeq"}.intersection(value),
            "v2 public payload must not expose entryId or entrySeq",
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


def main() -> int:
    try:
        common = json.loads(COMMON_PATH.read_text(encoding="utf-8"))
        model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
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
        header_sets = [
            ("common", common["requestHeaderExamples"]),
            ("submitSessionEvent", operation["requestHeaderExamples"]),
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
        questions = review["questions"]
        require(
            [question["id"] for question in questions]
            == ["Q2-request-shape", "Q3-success-response", "Q4-retry-policy"],
            "only Q2, Q3 and Q4 remain open; the confirmed Q1 must not reappear",
        )
        for question in questions:
            selected = [option for option in question["options"] if option.get("selected")]
            require(len(selected) == 1, f'{question["id"]} must have one recommended selection')
        subprocess.run([sys.executable, str(ROOT / "render_chat_events_v2.py"), "--check"], check=True)
    except (KeyError, OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"error: {error}")
        return 2
    print("Session Events v2 review snapshot is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

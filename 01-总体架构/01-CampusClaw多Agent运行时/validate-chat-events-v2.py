#!/usr/bin/env python3
"""Validate merged POST SSE decisions, preserved inputs and generated review."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMON_PATH = ROOT / "接口契约-v2" / "common.json"
MODEL_PATH = ROOT / "接口契约-v2" / "操作" / "01-submit-session-event.json"
USER_EVENT_TYPES = {"user.message", "user.interrupt", "user.tool_confirmation"}
STREAM_TYPES = {"agent.message", "agent.thinking", "agent.tool_call", "agent.tool_result", "session.status_idle"}
RETIRED_STREAM_TYPES = {"assistant.message", "assistant.thinking", "tool.call", "tool.result", "session.status.idle"}
CONFIRMED_CHOICES = {
    "M1-transport": "single-post-sse",
    "M2-receipt": "A-user-event-first",
    "M3-close-rule": "idle-closes-including-confirming",
    "M4-interrupt-delivery": "original-output-and-interrupt-receipt-shared-idle",
    "M5-interrupt-coordination": "database-durable-stop-and-instance-batch-polling",
    "M6-message-admission": "session-single-message-atomic-idle-to-running",
    "M7-interrupt-optimization": "post-commit-local-wakeup-deduplicated-waiters-measured-index",
    "S1-frame-format": "A-data-only",
    "S2-event-projection": "A-type-and-phase",
}
INTERRUPT_OPTIMIZATION = {
    "authority": "committed-database",
    "localWakeup": "after-commit-only",
    "pollingFallback": True,
    "waiterGrouping": "fixed-internal-execution",
    "registrationRecovery": "register-then-read-committed-terminal",
    "terminalDelivery": "receipt-first-once-per-response",
    "lastWaiterCleanup": "local-registration-only",
    "indexSelection": "gaussdb-plan-and-load-test",
    "pollingIntervalMs": None,
    "batchSize": None,
    "interruptWaitTimeoutMs": None,
    "toolTimeoutMs": None,
}
RESPONSE_INPUTS = {
    "200-message": "user.message",
    "200-confirming": "user.message",
    "200-tool-confirmation": "user.tool_confirmation",
    "200-interrupt": "user.interrupt",
    "200-message-interrupted": "user.message",
}

def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_public_payload(value: object) -> None:
    if isinstance(value, dict):
        require(
            not {"entryId", "entrySeq", "eventSeq", "runId", "executionId", "executionGeneration",
                 "targetExecutionId", "ownerInstanceId"}.intersection(value),
            "v2 public payload must not expose internal identifiers or sequences",
        )
        for child in value.values():
            validate_public_payload(child)
    elif isinstance(value, list):
        for child in value:
            validate_public_payload(child)


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



def validate_frame(event: dict, receipt: bool = False) -> None:
    validate_public_payload(event)
    require(event.get("type") in (USER_EVENT_TYPES if receipt else STREAM_TYPES),
            "receipt/output event is not in its allowed scope")
    require(isinstance(event.get("eventId"), str) and bool(event["eventId"]), "eventId is required")
    if receipt:
        require("phase" not in event, "receipt is a complete user event, not a preview")
    elif event["type"] in {"agent.message", "agent.thinking"}:
        require(event.get("phase") in {"delta", "completed"}, "text phase is required")
        require(isinstance(event.get("content"), str), "candidate text content must be a string")
    else:
        require("phase" not in event, "tool/idle events have no phase")
    if event.get("phase") == "delta":
        require("createdAt" not in event and bool(event["content"]), "delta must omit createdAt and be nonempty")
    else:
        require(isinstance(event.get("createdAt"), str), "complete event requires createdAt")
    if event["type"] in {"agent.tool_call", "agent.tool_result"}:
        require(bool(event.get("toolCallId")), "toolCallId is required")
    if event["type"] == "session.status_idle":
        require(event.get("reason") in {"done", "failed", "terminated", "confirming"}, "invalid candidate reason")


def parse_stream(stream: str) -> list[dict]:
    require(isinstance(stream, str) and stream.endswith("\n\n"), "SSE must terminate frames with blank lines")
    events = []
    for frame in stream.strip().split("\n\n"):
        if frame == ": ping":
            require(not events or events[-1]["type"] != "session.status_idle", "no ping after confirmed idle close")
            continue
        require(frame.startswith("data: ") and "\n" not in frame, "business frames must be data-only JSON")
        events.append(json.loads(frame[6:]))
    return events


def validate_headers(operation: dict) -> None:
    validate_access_token_rule(operation)
    expected_ids = {"jwt": "credential-jwt", "appkey": "credential-appkey"}
    for mode in operation["requestHeaderExamples"]:
        headers = {item["name"]: item for item in mode["headers"]}
        require(len(headers) == len(mode["headers"]), "duplicate Header")
        require(headers["Accept"]["value"] == "text/event-stream", "POST must request SSE")
        require(headers["Content-Type"]["value"] == "application/json", "POST body remains JSON")
        require(headers["X-HW-ID"]["value"] == expected_ids[mode["id"]], "credential ID example changed")
        require("用户凭据 ID" in headers["X-HW-ID"]["description"]
                and "不是公司、服务或应用标识" in headers["X-HW-ID"]["description"], "credential ID meaning changed")
        credential_name = "Authorization" if mode["id"] == "jwt" else "X-HW-APPKEY"
        require(headers[credential_name]["value"] == ("Bearer opaque-token" if mode["id"] == "jwt" else "opaque-appkey"),
                "confirmed credential example changed")
        require(all("<" not in item["value"] and ">" not in item["value"] for item in headers.values()),
                "use concrete non-production examples")


def validate_model(model: dict) -> None:
    operation, review = model["operation"], model["review"]
    require(operation["method"] == "POST" and operation["path"] == "/sessions/{sessionId}/events",
            "merged operation must be POST /events")
    require(operation["operationKey"] == "submitSessionEvent", "review operation identity changed")
    validate_headers(operation)
    validate_event_ordering_rule(review)
    require(review.get("interruptOptimization") == INTERRUPT_OPTIMIZATION,
            "preserve M7 guarantees without approving numerical defaults")
    require("中断查询优化已确认" in review["status"], "M7 approval must be visible")
    for clause in ("停止请求提交成功后", "数据库轮询兜底保留", "固定内部执行身份是等待结果的去重键",
                   "先登记等待再补读已提交终态", "同一终态每条响应最多投递一次",
                   "慢连接互不阻塞", "不删除停止请求或终态", "不预先冻结具体索引"):
        require(clause in operation["description"] and clause in review["notice"],
                f"missing visible M7 consistency rule: {clause}")
    body = operation["requestBody"]
    require(body["required"] and body["contentType"] == "application/json", "union request must remain JSON")
    inputs = {}
    for example in body["examples"]:
        value = example["value"]
        validate_public_payload(value)
        require(set(value) == {"event"}, "event wrapper must be preserved")
        inputs[value["event"]["type"]] = value["event"]
    require(set(inputs) == USER_EVENT_TYPES and len(body["examples"]) == 3, "preserve three input examples")
    require(isinstance(inputs["user.message"]["content"], list), "message content remains ordered array")

    all_types, receipt_types, response_ids = set(), set(), set()
    for response in operation["responses"]:
        require(response["id"] not in response_ids, "duplicate response ID")
        response_ids.add(response["id"])
        for payload in response["bodies"].values():
            if response["status"] != "200":
                require(response["headers"]["Content-Type"] == "application/json", "pre-header failure must be JSON")
                require(set(payload) == {"resCode", "resMsg"}, "errors must have no result field")
                continue
            require(response["headers"]["Content-Type"] == "text/event-stream", "POST success must be SSE")
            require(response["headers"]["Cache-Control"] == "no-store", "SSE must not be cached")
            frames = parse_stream(payload)
            require(len(frames) >= 2, "receipt and corresponding output are required")
            receipt = frames[0]
            validate_frame(receipt, receipt=True)
            kind = RESPONSE_INPUTS[response["id"]]
            require(receipt["type"] == kind, "receipt must correspond to this request")
            normalized = {key: value for key, value in receipt.items() if key not in {"eventId", "createdAt"}}
            require(normalized == inputs[kind], "complete receipt must preserve normalized submitted event")
            receipt_types.add(kind)
            completed = {receipt["eventId"]}
            for index, event in enumerate(frames[1:], 1):
                validate_frame(event)
                require(event["eventId"] not in completed, "no repeated complete event or receipt")
                if event.get("phase") != "delta":
                    completed.add(event["eventId"])
                if event["type"] == "session.status_idle":
                    require(index == len(frames) - 1, "confirmed idle closes this response; no later output")
                all_types.add(event["type"])
            require(frames[-1]["type"] == "session.status_idle", "normal-close example must end at matching idle")
    require(set(RESPONSE_INPUTS).issubset(response_ids), "examples must cover message, confirming, confirmation and interrupt")
    streams = {item["id"]: parse_stream(item["bodies"]["default"])
               for item in operation["responses"] if item["status"] == "200"}
    interrupt = streams["200-interrupt"]
    require(len(interrupt) == 2, "interrupt response must contain only its receipt and matching stop idle")
    require(streams["200-message-interrupted"][-1] == interrupt[-1],
            "original and interrupt responses must deliver the same idle event, including eventId")
    require(receipt_types == USER_EVENT_TYPES and all_types == STREAM_TYPES, "missing receipt or basic output examples")
    require(review.get("confirmedChoices") == CONFIRMED_CHOICES, "preserve exact confirmed transport/receipt/closing/S1/S2")
    require(set(review["confirmedEventTypes"]) == STREAM_TYPES, "confirmed output type names changed")
    require(review["questions"] == [], "do not reopen confirmed choices")
    require("合并 POST 接口整体确认" in review["pendingReview"], "whole operation must remain pending")
    require("合并接口评审中" in review["status"], "do not mark merged operation fully confirmed")
    require("完整 user.* 首帧回执已确认" in review["status"], "receipt approval must be visible")
    require("结束规则已确认" in review["status"], "closing approval must be visible")
    require("中断推送分工已确认" in review["status"], "interrupt delivery approval must be visible")
    require("数据库中断机制已确认" in review["status"], "database interruption approval must be visible")
    for clause in ("同一短事务中绑定具体内部执行", "批量检查本机活动执行的停止请求",
                   "同一条权威结束事件", "当前仅依赖数据库", "Redis 仅在后续有必要时评估"):
        require(clause in operation["description"], f"missing database interruption constraint: {clause}")
    require("检查周期" in " ".join(review["pendingReview"]), "polling interval must remain pending")
    require("等待工具确认时也关闭" in operation["description"], "confirmation wait must also close the response")
    require("idle reason" in " ".join(review["pendingReview"]), "closing approval must not confirm reason literals")
    require("三种用户事件均必须携带 access-token" in review["notice"], "preserve three-type token rule")
    require(review["decisionHistory"]["S3-user-events"]["previous"] == "A-user-events-receipt-history-only",
            "record the explicitly superseded S3")
    require("用户明确调整" in review["decisionHistory"]["S3-user-events"]["status"], "S3 adjustment needs explicit attribution")
    require("不适用于合并 POST" in review["decisionHistory"]["S4-read-access-token"]["status"],
            "retired GET token policy must not leak into POST")
    require(not any(name in json.dumps(model, ensure_ascii=False) for name in RETIRED_STREAM_TYPES),
            "do not restore v1 or rejected candidate type names")


def validate_negative_regressions(model: dict) -> int:
    mutations = []
    def changed(label, edit):
        candidate = copy.deepcopy(model)
        edit(candidate)
        mutations.append((label, candidate))
    changed("GET method", lambda m: m["operation"].update(method="GET"))
    changed("JSON success", lambda m: m["operation"]["responses"][0]["headers"].update({"Content-Type": "application/json"}))
    changed("missing token", lambda m: m["operation"]["requestHeaderExamples"][0]["headers"][2].update(required=False))
    changed("reopened receipt", lambda m: m["review"].update(questions=[{"id": "M2-receipt"}]))
    changed("false approval", lambda m: m["review"].update(pendingReview=[]))
    changed("missing database decision", lambda m: m["operation"].update(
        description=m["operation"]["description"].replace("当前仅依赖数据库", "当前依赖 Redis")))
    changed("missing fixed target", lambda m: m["operation"].update(
        description=m["operation"]["description"].replace("同一短事务中绑定具体内部执行", "按最新执行绑定")))
    changed("missing M7 status", lambda m: m["review"].update(
        status=m["review"]["status"].replace("中断查询优化已确认", "待定")))
    changed("missing M7 model", lambda m: m["review"].pop("interruptOptimization"))
    for field, value in INTERRUPT_OPTIMIZATION.items():
        changed(f"changed M7 {field}", lambda m, key=field, original=value:
                m["review"]["interruptOptimization"].update({key: 500 if original is None else "unconfirmed"}))
        changed(f"missing M7 {field}", lambda m, key=field: m["review"]["interruptOptimization"].pop(key))
    for field in ("description", "notice"):
        section = "operation" if field == "description" else "review"
        changed(f"missing visible M7 in {field}", lambda m, key=field, area=section: m[area].update(
            {key: m[area][key].replace("先登记等待再补读已提交终态", "只等待通知")}))
    for choice in CONFIRMED_CHOICES:
        changed(choice, lambda m, key=choice: m["review"]["confirmedChoices"].update({key: "unconfirmed"}))
    original = model["operation"]["responses"][0]["bodies"]["default"]
    first, rest = original.split("\n\n", 1)
    for label, payload in (
        ("missing receipt", rest),
        ("duplicate receipt", first + "\n\n" + original),
        ("named SSE", original.replace("data: ", "event: user.message\ndata: ", 1)),
        ("public sequence", original.replace('"type":"user.message"', '"entrySeq":1,"type":"user.message"', 1)),
        ("unrelated receipt", original.replace('"type":"user.message"', '"type":"user.interrupt"', 1)),
        ("incomplete receipt", original.replace('"content":[', '"unexpected":[', 1)),
        ("receipt phase", original.replace('"type":"user.message"', '"phase":"completed","type":"user.message"', 1)),
        ("missing text phase", original.replace(',"phase":"delta"', "", 1)),
        ("later unrelated user", original + first + "\n\n"),
        ("ping after idle", original + ": ping\n\n"),
    ):
        changed(label, lambda m, value=payload: m["operation"]["responses"][0]["bodies"].update(default=value))
    confirming_index = next(index for index, response in enumerate(model["operation"]["responses"])
                            if response["id"] == "200-confirming")
    confirming = model["operation"]["responses"][confirming_index]["bodies"]["default"]
    changed("ping after confirmation idle", lambda m: m["operation"]["responses"][confirming_index]["bodies"].update(
        default=confirming + ": ping\n\n"))
    changed("output after confirmation idle", lambda m: m["operation"]["responses"][confirming_index]["bodies"].update(
        default=confirming + rest.split("\n\n", 1)[0] + "\n\n"))
    interrupt_index = next(index for index, response in enumerate(model["operation"]["responses"])
                           if response["id"] == "200-interrupt")
    interrupt = model["operation"]["responses"][interrupt_index]["bodies"]["default"]
    interrupt_receipt, interrupt_idle = interrupt.split("\n\n", 1)
    changed("agent output copied to interrupt", lambda m: m["operation"]["responses"][interrupt_index]["bodies"].update(
        default=interrupt_receipt + "\n\n" + rest.split("\n\n", 1)[0] + "\n\n" + interrupt_idle))
    changed("different stop eventId", lambda m: m["operation"]["responses"][interrupt_index]["bodies"].update(
        default=interrupt.replace('"eventId":"38e397c80d5a4f3ba7916df3bbf0a936"', '"eventId":"different-idle"')))
    for label, candidate in mutations:
        try:
            validate_model(candidate)
        except (KeyError, ValueError):
            continue
        raise ValueError(f"negative regression accepted: {label}")
    for field in ("executionGeneration", "targetExecutionId", "ownerInstanceId"):
        try:
            validate_frame({"eventId": "example", "type": "agent.message", "phase": "delta",
                            "content": "example", field: "internal"})
        except ValueError:
            continue
        raise ValueError(f"internal execution identity exposed: {field}")
    for name in RETIRED_STREAM_TYPES:
        try:
            validate_frame({"type": name, "eventId": "example"})
        except ValueError:
            continue
        raise ValueError(f"retired type accepted: {name}")
    return len(mutations) + len(RETIRED_STREAM_TYPES) + 3


def validate_review_pages() -> None:
    spec = importlib.util.spec_from_file_location("runtime_contract_validator", ROOT / "validate-chat-http-v1.py")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    source = (ROOT / "chat-events-v2-review.html").read_text(encoding="utf-8")
    parser = validator.ContractHtmlParser()
    parser.feed(source)
    models, scripts = validator.parse_generated_models(parser)
    require(len(models) == parser.static_review_count == len(scripts) == 1, "show one current operation")
    require(models[0]["operation"]["operationKey"] == "submitSessionEvent", "show merged POST")
    validate_model(models[0])
    validator.validate_executable_script(scripts[0])
    visible = " ".join(parser.visible_text)
    for text in ("作用", "调用上下文 Header", "参数与请求体", "响应", "首个业务帧", "未整体确认合并接口",
                 "结束规则已确认", "等待工具确认时也关闭", "中断推送分工已确认", "数据库中断机制已确认",
                 "中断查询优化已确认", "先登记等待再补读已提交终态", "同一终态每条响应最多投递一次"):
        require(text in visible, f"no-JavaScript page is missing {text}")
    require("data-question-id=" not in source, "confirmed receipt must not remain a question")
    require("data-label" in source and "max-width: 680px" in source, "responsive rules missing")
    retired = (ROOT / "chat-events-v2-confirmed.html").read_text(encoding="utf-8")
    require("原独立 POST JSON 方案已被合并方案替代" in retired, "retire stale whole-operation approval")
    require("chat-events-v2-review.html" in retired and "data-operation-review" not in retired,
            "old confirmed page must link current review, not display an approved operation")


def main() -> int:
    try:
        common = json.loads(COMMON_PATH.read_text(encoding="utf-8"))
        model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
        require(common["reviewState"] == {"currentOperation": "submitSessionEvent", "confirmedOperations": []},
                "current merged POST remains in review")
        require(sorted(MODEL_PATH.parent.glob("*.json")) == [MODEL_PATH], "retired GET stream model must not remain active")
        validate_model(model)
        negative_count = validate_negative_regressions(model)
        subprocess.run([sys.executable, str(ROOT / "render_chat_events_v2.py"), "--check"], check=True)
        validate_review_pages()
    except (KeyError, OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"error: {error}")
        return 2
    print(f"Merged POST SSE review is valid; {negative_count} negative regressions rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

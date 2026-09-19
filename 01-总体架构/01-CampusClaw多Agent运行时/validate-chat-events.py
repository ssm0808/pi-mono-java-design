#!/usr/bin/env python3
"""Validate POST SSE and ListEvents models, examples and generated review pages."""

from __future__ import annotations

import copy
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

from question_contract import validate_question_event, validate_answer_event, validate_question_regressions

ROOT = Path(__file__).resolve().parent
COMMON_PATH = ROOT / "事件契约" / "common.json"
MODEL_PATH = ROOT / "事件契约" / "操作" / "01-submit-session-event.json"
HISTORY_PATH = ROOT / "事件契约" / "操作" / "02-list-session-events.json"
USER_EVENT_TYPES = {"user.message", "user.interrupt", "user.tool_confirmation", "user.plan_confirmation", "user.question_answer"}
STREAM_TYPES = {"agent.message", "agent.thinking", "agent.tool_call", "agent.tool_result", "agent.todo_updated", "agent.plan", "agent.question", "session.mode_changed", "session.status_idle"}
HISTORY_TYPES = {"session.model_changed", "session.thinking_changed", "session.mode_changed", "session.compacted"}
BATCH_CHOICES = {f"BATCH-20260908-1-{group}": "A-recommended" for group in ("tools", "events", "lifecycle", "integration")}
RETIRED_STREAM_TYPES = {"assistant.message", "assistant.thinking", "tool.call", "tool.result", "session.status.idle"}
CONFIRMED_CHOICES = {
    "M1-transport": "single-post-sse",
    "M2-receipt": "A-user-event-first",
    "M3-close-rule": "idle-closes-including-confirming",
    "M4-interrupt-delivery": "original-output-and-interrupt-receipt-shared-idle",
    "M5-interrupt-coordination": "database-durable-stop-and-instance-batch-polling",
    "M6-message-admission": "session-single-message-atomic-idle-to-running",
    "M7-interrupt-optimization": "post-commit-local-wakeup-deduplicated-waiters-measured-index",
    "M8-control-retirement": "remove-standalone-controls-follow-up-future-only",
    "S1-frame-format": "A-data-only",
    "S2-event-projection": "A-type-and-phase",
    "L5-agent-message-content": "A-string",
    "L6-tool-call-arguments": "A-object",
    "L7-tool-result-content": "A-content-blocks",
    "L8-tool-result-types": "A-text-only",
    "L9-mate-tool-identity": "A-runtime-wrapper",
    "L10-tool-result-outcome": "A-is-error",
}
CONFIRMED_CHOICES.update(BATCH_CHOICES)
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
    "200-tool-success": "user.message",
    "200-todo-updated": "user.message",
    "200-execution-failed": "user.message",
    "200-plan-review": "user.message",
    "200-plan-approved": "user.plan_confirmation",
    "200-plan-revised": "user.plan_confirmation",
    "200-question-asking": "user.message",
    "200-question-answered": "user.question_answer",
}

def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)



def java_whitespace(char: str) -> bool:
    return char in "\t\n\v\f\r\x1c\x1d\x1e\x1f " or ord(char) in {
        0x1680, *range(0x2000, 0x2007), *range(0x2008, 0x200B), 0x2028, 0x2029, 0x205F, 0x3000}


def bounded_nonblank(value: object, limit: int) -> bool:
    return (isinstance(value, str) and any(not java_whitespace(c) for c in value)
            and len(value.encode("utf-16-le")) // 2 <= limit)


def validate_plan_confirmation(event: dict, receipt: bool = False) -> None:
    fields = {"type", "targetEventId", "result"}
    if receipt:
        fields |= {"eventId", "createdAt"}
    require(isinstance(event.get("result"), str) and event["result"] in {"approve", "revise"},
            "invalid plan decision")
    if event["result"] == "revise" and "feedback" in event:
        fields.add("feedback")
        require(bounded_nonblank(event["feedback"], 4096), "invalid revision feedback")
    require(set(event) == fields, "plan confirmation has unknown, missing or conditional fields")
    require(bounded_nonblank(event["targetEventId"], 128), "invalid plan target identity")


def validate_public_payload(value: object) -> None:
    if isinstance(value, dict):
        require(
            not {"entryId", "entrySeq", "eventSeq", "runId", "executionId", "executionGeneration",
                 "targetExecutionId", "ownerInstanceId"}.intersection(value),
            "public event payload must not expose internal identifiers or sequences",
        )
        for child in value.values():
            validate_public_payload(child)
    elif isinstance(value, list):
        for child in value:
            validate_public_payload(child)


def validate_access_token_rule(operation: dict) -> None:
    policy = operation.get("credentialPolicy", {})
    require(policy.get("requestHeadersRequired") is False,
            "POST Events credential Headers must be optional")
    require(policy.get("entryRejectsMissingCredentials") is False,
            "POST Events must not reject missing credentials at the entry")
    require(policy.get("clawChecksCredentialCompleteness") is False,
            "POST Events Claw must not check credential completeness")
    require(policy.get("mateDecidesCredentialFailure") is True,
            "POST Events Mate must decide credential failure")
    require("tool execute" in policy.get("toolExecuteFailure", ""),
            "POST Events must defer missing credential failure to tool execute")
    modes = operation["requestHeaderExamples"]
    require(
        len(modes) == 2 and {mode["id"] for mode in modes} == {"jwt", "appkey"},
        "POST Events must retain both Header modes",
    )
    for mode in modes:
        tokens = [header for header in mode["headers"] if header["name"] == "access-token"]
        require(len(tokens) == 1, f"{mode['id']} must contain exactly one access-token Header")
        token = tokens[0]
        require(token.get("required") is False, f"{mode['id']} access-token must be optional")
        require(token["value"] == "opaque-access-token", "confirmed access-token example must be preserved")
        require(
            "可选" in token["description"] and "Claw 不检查凭据完整性" in token["description"]
            and "Mate execute" in token["description"],
            f"{mode['id']} must state deferred credential failure",
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



def validate_frame(event: dict, receipt: bool = False, history: bool = False) -> None:
    validate_public_payload(event)
    require(event.get("type") in (USER_EVENT_TYPES if receipt else STREAM_TYPES | (HISTORY_TYPES if history else {"session.compacted"})),
            "receipt/output event is not in its allowed scope")
    require(isinstance(event.get("eventId"), str) and bool(event["eventId"]), "eventId is required")
    if receipt:
        require("phase" not in event, "receipt is a complete user event, not a preview")
    elif event["type"] in {"agent.message", "agent.thinking"}:
        require(event.get("phase") in {"delta", "completed"}, "text phase is required")
        message = ("confirmed completed agent.message content must be a string"
                   if event["type"] == "agent.message" and event["phase"] == "completed"
                   else "candidate text content must be a string")
        require(isinstance(event.get("content"), str), message)
    else:
        require("phase" not in event, "tool/idle events have no phase")
    if event.get("phase") == "delta":
        require("createdAt" not in event and bool(event["content"]), "delta must omit createdAt and be nonempty")
    else:
        require(isinstance(event.get("createdAt"), str) and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z", event["createdAt"]) is not None, "complete event requires createdAt")
    if event["type"] in {"agent.tool_call", "agent.tool_result"}:
        require(bool(event.get("toolCallId")), "toolCallId is required")
    if event["type"] == "agent.tool_call":
        require(isinstance(event.get("arguments"), dict), "confirmed tool arguments must be a JSON object")
    if event["type"] == "agent.tool_result":
        require(type(event.get("isError")) is bool, "every tool result must contain a boolean isError")
        require("status" not in event, "confirmed isError must not be replaced or duplicated by status")
        content = event.get("content")
        require(isinstance(content, list) and len(content) >= 1 and all(isinstance(block, dict) for block in content),
                "confirmed tool result content must be an array of content blocks")
        require(all(set(block) == {"type", "text"} and block["type"] == "text"
                    and isinstance(block["text"], str) for block in content),
                "current tool results must contain only public text blocks, never JSON or images")
    if event["type"] == "user.plan_confirmation":
        validate_plan_confirmation(event, receipt=True)
    if event["type"] == "agent.question":
        validate_question_event(event)
    if event["type"] == "user.question_answer":
        validate_answer_event(event, receipt=True)
    if event["type"] == "agent.plan":
        require(set(event) == {"eventId", "type", "createdAt", "sourceEventId", "toolCallId", "content"},
                "plan must use the complete review event shape")
        require(isinstance(event["toolCallId"], str)
                and any(not java_whitespace(c) for c in event["toolCallId"]), "plan requires tool call identity")
        content = event["content"]
        require(bounded_nonblank(content, 262144), "plan Markdown is required and bounded")
        first = next(line for line in content.splitlines() if any(not java_whitespace(c) for c in line))
        require(first.startswith("# "), "plan first nonblank line must start with a Markdown heading")
    if event["type"] == "agent.todo_updated":
        require(set(event) == {"eventId", "type", "createdAt", "sourceEventId", "toolCallId", "todos"},
                "task snapshot must use the explicit event shape")
        require(isinstance(event["toolCallId"], str) and bool(event["toolCallId"]), "task provenance required")
        todos = event["todos"]
        require(isinstance(todos, list) and len(todos) <= 100, "task snapshot must be a bounded full array")
        contents = set()
        active = 0
        for item in todos:
            require(isinstance(item, dict) and set(item) == {"content", "status"}, "task item fields differ")
            content = item["content"]
            require(isinstance(content, str) and bool(content) and len(content.encode("utf-16-le")) // 2 <= 1024,
                    "task content must be nonempty and bounded")
            require(not java_whitespace(content[0]) and not java_whitespace(content[-1]),
                    "task content must already be normalized")
            require(content not in contents, "duplicate task content")
            contents.add(content)
            require(item["status"] in {"pending", "in_progress", "completed"}, "invalid task status")
            active += item["status"] == "in_progress"
        require(active <= 1, "at most one task may be in progress")
    if event["type"] == "session.status_idle":
        require(event.get("reason") in {"done", "failed", "terminated", "confirming"}, "invalid candidate reason")

    if event["type"] in STREAM_TYPES - {"session.mode_changed"}:
        require(isinstance(event.get("sourceEventId"), str) and bool(event["sourceEventId"]), "output needs original message sourceEventId")
    if event["type"] == "user.interrupt":
        require(isinstance(event.get("targetEventId"), str) and bool(event["targetEventId"]), "interrupt needs targetEventId")
    if event["type"] == "agent.tool_call":
        require(type(event.get("requiresConfirmation")) is bool, "confirmation flag is required")
        require(isinstance(event.get("toolName"), str) and bool(event["toolName"]), "toolName required")
        require("label" not in event, "tool call must not duplicate displayName as label")
        if "displayName" in event:
            name = event["displayName"]
            require(isinstance(name, str) and bool(name.strip()) and name == name.strip(),
                    "displayName must be normalized nonempty text or omitted")
    contract = json.loads(COMMON_PATH.read_text())["eventContract"]
    if event["type"] == "agent.tool_result":
        require(event.get("errorCode") in contract["toolErrorCodes"] if event["isError"] else "errorCode" not in event,
                "failure requires stable code; success omits it")
        require(not {"errorMessage", "details", "status"}.intersection(event), "no duplicate or private tool fields")
    if event["type"] == "session.status_idle":
        if event["reason"] == "failed":
            require(event.get("errorCode") in contract["executionErrorCodes"] and isinstance(event.get("message"), str)
                    and bool(event["message"]), "failed idle needs safe code and message")
        else:
            require(not {"errorCode", "message"}.intersection(event), "nonfailure idle omits errors")
    if "usage" in event:
        require(event["type"] == "agent.message" and event.get("phase") == "completed", "usage only on complete message")
        usage = event["usage"]
        tokens = {"input", "output", "cacheRead", "cacheWrite", "totalTokens"}
        require(isinstance(usage, dict) and tokens <= set(usage) <= tokens | {"cost"}, "usage fields differ")
        require(all(type(usage[k]) is int and usage[k] >= 0 for k in tokens), "nonnegative token integers required")
        if "cost" in usage:
            cost = usage["cost"]
            require(isinstance(cost, dict) and set(cost) == {"input", "output", "cacheRead", "cacheWrite", "total"}
                    and all(type(v) in (int, float) and v >= 0 for v in cost.values()), "invalid USD cost")
    if event["type"] in HISTORY_TYPES:
        require("phase" not in event, "domain changes are complete")
        if event["type"] == "session.model_changed":
            require("sourceEventId" not in event and event.get("reason") in {"requested", "agentRefresh"}
                    and all(isinstance(event.get(k), str) and event[k] for k in ("previousModelId", "modelId"))
                    and event["previousModelId"] != event["modelId"], "invalid model change")
        elif event["type"] == "session.thinking_changed":
            require("sourceEventId" not in event and event.get("reason") in {"requested", "modelCapability"}
                    and all(type(event.get(k)) is bool for k in ("previousThinking", "thinking"))
                    and event["previousThinking"] != event["thinking"], "invalid thinking change")
        elif event["type"] == "session.mode_changed":
            fields = {"eventId", "type", "createdAt", "previousMode", "mode", "reason"}
            if event.get("reason") == "planApproved":
                fields |= {"sourceEventId", "confirmationEventId"}
                require(event.get("previousMode") == "plan" and event.get("mode") == "build"
                        and bounded_nonblank(event.get("sourceEventId"), 128)
                        and bounded_nonblank(event.get("confirmationEventId"), 128), "invalid approved mode change")
            else:
                require(history and event.get("reason") == "requested", "requested mode change is outside allowed scope; history only")
                require(event.get("previousMode") in {"plan", "build"} and event.get("mode") in {"plan", "build"}
                        and event["previousMode"] != event["mode"], "invalid requested mode change")
            require(set(event) == fields, "mode change conditional fields differ")
        else:
            require(event.get("reason") in {"manual", "threshold", "overflow"}
                    and all(type(event.get(k)) is int and event[k] >= 0 for k in ("tokensBefore", "estimatedTokensAfter")), "invalid compaction")
            require(("sourceEventId" in event) == (event["reason"] != "manual"), "automatic compaction needs root only")
            require(not {"summary", "firstKeptEntryId", "usage", "_discardedEntryId"}.intersection(event), "private compaction state leaked")


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
        require(headers["Accept"].get("required") is True and headers["Content-Type"].get("required") is True,
                "POST transport Headers must remain required")
        require(all(item.get("required") is False for name, item in headers.items()
                    if name not in {"Accept", "Content-Type"}),
                "POST credential Headers must be optional")
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
        if value["event"]["type"] == "user.plan_confirmation":
            validate_plan_confirmation(value["event"])
        if value["event"]["type"] == "user.question_answer":
            validate_answer_event(value["event"])
    require(set(inputs) == USER_EVENT_TYPES and len(body["examples"]) == 6, "cover five input types and both plan decisions")
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
            require(any(normalized == example["value"]["event"] for example in body["examples"]),
                    "complete receipt must preserve normalized submitted event")
            receipt_types.add(kind)
            completed = {receipt["eventId"]}
            for index, event in enumerate(frames[1:], 1):
                validate_frame(event)
                root = receipt["eventId"] if kind == "user.message" else inputs["user.interrupt"]["targetEventId"]
                require(event.get("sourceEventId") == root, "output must keep the original message identity")
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
    mate_call = next(event for event in streams["200-confirming"] if event["type"] == "agent.tool_call")
    require(mate_call["toolName"] == "CallMateTool" and mate_call["arguments"] == {
        "tool": "isolate_campus_port",
        "args": {"deviceName": "SW-DC-01", "portName": "GigabitEthernet0/0/24"},
    }, "confirmed Mate example must preserve Runtime name and tool/args wrapping")
    interrupt = streams["200-interrupt"]
    require(interrupt[0]["targetEventId"] == streams["200-message-interrupted"][0]["eventId"], "interrupt target must be original root")
    require(len(interrupt) == 2, "interrupt response must contain only its receipt and matching stop idle")
    require(streams["200-message-interrupted"][-1] == interrupt[-1],
            "original and interrupt responses must deliver the same idle event, including eventId")
    require(receipt_types == USER_EVENT_TYPES and all_types == STREAM_TYPES, "missing receipt or basic output examples")
    require(review.get("confirmedChoices") == CONFIRMED_CHOICES,
            "preserve exact confirmed transport/receipt/closing/S1/S2/L5/L6/L7/L8/L9/L10")
    require("L5 已确认" in operation["description"] and "L5 已确认" in review["notice"],
            "completed content approval must be visible in POST")
    require("L6 已确认" in operation["description"] and "L6 已确认" in review["notice"],
            "tool arguments approval must be visible in POST")
    require("L7 已确认" in operation["description"] and "L7 已确认" in review["notice"],
            "tool result array approval must be visible in POST")
    require("L8 已确认" in operation["description"] and "L8 已确认" in review["notice"],
            "text-only tool result approval must be visible in POST")
    require("L9 已确认" in operation["description"] and "L9 已确认" in review["notice"],
            "Mate Runtime wrapper approval must be visible in POST")
    require("L10 已确认" in operation["description"] and "L10 已确认" in review["notice"],
            "tool result boolean outcome approval must be visible in POST")
    require(set(review["confirmedEventTypes"]) == STREAM_TYPES, "confirmed output type names changed")
    require(review["questions"] == [], "do not reopen confirmed choices")
    require(review["pendingReview"] == [] and review["deliveryState"] == "implementation-ready", "no unapproved product gate remains")
    require("目标契约已定稿" in review["status"], "target delivery status required")
    require("完整 user.* 首帧回执已确认" in review["status"], "receipt approval must be visible")
    require("结束规则已确认" in review["status"], "closing approval must be visible")
    require("中断推送分工已确认" in review["status"], "interrupt delivery approval must be visible")
    require("数据库中断机制已确认" in review["status"], "database interruption approval must be visible")
    for clause in ("同一短事务中绑定具体内部执行", "批量检查本机活动执行的停止请求",
                   "同一条权威结束事件", "当前仅依赖数据库", "Redis 仅在后续有必要时评估"):
        require(clause in operation["description"], f"missing database interruption constraint: {clause}")
    require("检查周期" in " ".join(review["implementationCalibration"]), "polling interval needs implementation calibration")
    require("等待工具确认时也关闭" in operation["description"], "confirmation wait must also close the response")
    require(operation.get("credentialPolicy", {}).get("requestHeadersRequired") is False,
            "credential Header policy must remain optional")
    require(operation["credentialPolicy"].get("clawChecksCredentialCompleteness") is False,
            "Claw must not check credential completeness")
    require(operation["credentialPolicy"].get("mateDecidesCredentialFailure") is True,
            "Mate must decide credential failure")
    require(review.get("credentialPolicyChange", {}).get("status") == "confirmed",
            "credential Header change must be explicitly confirmed")
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
    changed("reintroduced required token", lambda m: m["operation"]["requestHeaderExamples"][0]["headers"][2].update(required=True))
    changed("entry credential rejection", lambda m: m["operation"]["credentialPolicy"].update(entryRejectsMissingCredentials=True))
    changed("reopened receipt", lambda m: m["review"].update(questions=[{"id": "M2-receipt"}]))
    changed("reopened product gate", lambda m: m["review"].update(pendingReview=["whole approval"]))
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
    for label, edit in (
        ("expanded business tool name", lambda e: e.update(toolName="isolate_campus_port")),
        ("flattened business arguments", lambda e: e.update(arguments=e["arguments"]["args"])),
        ("missing business tool name", lambda e: e["arguments"].pop("tool")),
        ("business args string", lambda e: e["arguments"].update(args="{}")),
        ("public Mate internal toolId", lambda e: e["arguments"].update(toolId="internal-tool-id")),
    ):
        frames = parse_stream(confirming)
        edit(next(event for event in frames if event["type"] == "agent.tool_call"))
        invalid = "".join("data: " + json.dumps(event, ensure_ascii=False) + "\n\n" for event in frames)
        changed(label, lambda m, value=invalid:
                m["operation"]["responses"][confirming_index]["bodies"].update(default=value))
    for arguments in ('{"port":"GE0/0/1"}', [], None, 1, True):
        frames = parse_stream(confirming)
        next(event for event in frames if event["type"] == "agent.tool_call")["arguments"] = arguments
        invalid = "".join("data: " + json.dumps(event, ensure_ascii=False) + "\n\n" for event in frames)
        changed(f"non-object tool arguments: {arguments!r}",
                lambda m, value=invalid: m["operation"]["responses"][confirming_index]["bodies"].update(default=value))
    result_index = next(index for index, response in enumerate(model["operation"]["responses"])
                        if response["id"] == "200-tool-confirmation")
    result_stream = model["operation"]["responses"][result_index]["bodies"]["default"]
    for label, edit in (
        ("missing isError", lambda e: e.pop("isError")),
        ("null isError", lambda e: e.update(isError=None)),
        ("integer isError", lambda e: e.update(isError=1)),
        ("zero isError", lambda e: e.update(isError=0)),
        ("string isError", lambda e: e.update(isError="true")),
        ("array isError", lambda e: e.update(isError=[])),
        ("extra outcome status", lambda e: e.update(status="failed")),
    ):
        frames = parse_stream(result_stream)
        edit(next(event for event in frames if event["type"] == "agent.tool_result"))
        invalid = "".join("data: " + json.dumps(event, ensure_ascii=False) + "\n\n" for event in frames)
        changed(label, lambda m, value=invalid:
                m["operation"]["responses"][result_index]["bodies"].update(default=value))
    for outcome in (False, True):
        event = copy.deepcopy(next(e for e in parse_stream(result_stream) if e["type"] == "agent.tool_result"))
        event.update(isError=outcome, content=[{"type": "text", "text": "failed" if outcome else "completed"}])
        if outcome:
            event["errorCode"] = "TOOL_EXECUTION_FAILED"
        else:
            event.pop("errorCode", None)
        validate_frame(event)
    for content in ([], "text", {"type": "text", "text": "text"}, None, 1, True, ["text"], [None],
                    [{"type": "json", "data": {"status": "done"}}],
                    [{"type": "image", "data": "opaque", "mimeType": "image/png"}],
                    [{"type": "text", "text": {"status": "done"}}],
                    [{"type": "text", "text": None}],
                    [{"type": "text", "text": "text", "details": {"internal": True}}]):
        frames = parse_stream(result_stream)
        next(event for event in frames if event["type"] == "agent.tool_result")["content"] = content
        invalid = "".join("data: " + json.dumps(event, ensure_ascii=False) + "\n\n" for event in frames)
        changed(f"invalid tool result content container: {content!r}",
                lambda m, value=invalid: m["operation"]["responses"][result_index]["bodies"].update(default=value))
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


def complete_streams(post: dict) -> dict:
    return {item["id"]: [event for event in parse_stream(item["bodies"]["default"])
                         if event.get("phase") != "delta"]
            for item in post["operation"]["responses"] if item["status"] == "200" and item["headers"]["Content-Type"] == "text/event-stream"}


def validate_history_model(model: dict, post: dict) -> None:
    operation, review = model["operation"], model["review"]
    require((operation["method"], operation["path"], operation["operationKey"]) ==
            ("GET", "/sessions/{sessionId}/events", "listSessionEvents"), "history is GET events, not a stream")
    require(operation["requestBody"]["contentType"] is None
            and not operation["requestBody"]["required"]
            and operation["requestBody"]["example"] is None, "GET history has no request body")
    modes = operation["requestHeaderExamples"]
    require(len(modes) == 2 and {m["id"] for m in modes} == {"jwt", "appkey"}, "preserve both read modes")
    for mode in modes:
        headers = {h["name"]: h for h in mode["headers"]}
        require(len(headers) == len(mode["headers"]), "duplicate read Header")
        require("access-token" not in headers, "history must not ask for a tool token")
        require(all(headers[name].get("required") is False for name in headers),
                "history credential and transport Headers must remain optional")
        require(headers["X-HW-ID"]["value"] == f"credential-{mode['id']}", "read credential example drift")
        require("用户凭据 ID" in headers["X-HW-ID"]["description"], "credential ID is not a company ID")
        name = "Authorization" if mode["id"] == "jwt" else "X-HW-APPKEY"
        require(headers[name]["value"] == ("Bearer opaque-token" if name == "Authorization" else "opaque-appkey"),
                "read credential value drift")
        require(headers["Accept"]["value"] == "application/json", "history requests JSON")
    require([p["name"] for p in operation["parameters"] if p.get("in") == "query"] == ["limit", "page"],
            "do not introduce unreviewed query parameters")
    parameters = {p["name"]: p for p in operation["parameters"] if p.get("in") == "query"}
    require(parameters["page"]["schema"] == "integer >= 1; default 1", "page is a one-based integer")
    require(parameters["limit"]["schema"] == "integer 1..200; default 50",
            "confirmed default 50 and max 200 must not drift")
    require(review["inheritedRules"] == {
        "eventIdentity": "eventId", "completeEventProjection": "same-as-post-sse",
        "ordering": "committed-causal-order", "deltaHistory": False,
    }, "history must retain identity and projection, without reviving a fixed snapshot")
    require(review["confirmedPagination"] == {
        "direction": "oldest-first", "pageType": "positive-integer", "firstPage": 1, "defaultPage": 1,
        "fixedSnapshot": False, "cursorEncryption": False, "nextPage": "integer-or-null",
        "sameLimitAcrossPages": True, "readWhileRunning": True,
        "defaultLimit": 50, "maxLimit": 200, "responseFields": ["events", "nextPage"],
        "outOfRangePage": "empty-success",
    }, "ordinary pagination is confirmed, without a cross-page snapshot or idle-only restriction")
    proposal = review["historyProposal"]
    require(proposal == {
        "scope": "current-branch-per-request", "thinkingFilter": "persisted-original-thinking-current-access",
        "readToolToken": False,
    }, "keep only the remaining candidates, not cursor keys, bindings or expiry")
    require(review["confirmedChoices"] == {
        "L1-page-direction": "A-oldest-first", "L1-page-format": "one-based-integer",
        "L1-consistency": "no-fixed-snapshot",
        "L2-page-size": "B-default50-max200", "L3-page-metadata": "A-events-nextPage-only",
        "L4-out-of-range-page": "A-empty-success",
        "L5-agent-message-content": "A-string",
        "L6-tool-call-arguments": "A-object",
        "L7-tool-result-content": "A-content-blocks",
        "L8-tool-result-types": "A-text-only",
        "L9-mate-tool-identity": "A-runtime-wrapper",
        "L10-tool-result-outcome": "A-is-error",
        **BATCH_CHOICES,
    } and review["pendingReview"] == [] and review["deliveryState"] == "implementation-ready",
            "pagination, completed content, tool arguments and result container are approved, not the whole operation")
    require(review["questions"] == [], "do not reopen the confirmed semantic batch")
    batch = review["batchReview"]
    require(batch["status"] == "confirmed" and batch["version"] == "2026-09-08.1" and batch.get("confirmedBy"), "record actual batch approval")
    require([item["id"] for item in batch["items"]] == [f"B{i:02}" for i in range(1, 16)], "retain all fifteen semantic decisions")
    require("L5 已确认" in operation["description"] and "L5 已确认" in review["notice"],
            "completed content approval must be visible in history")
    require("L6 已确认" in operation["description"] and "L6 已确认" in review["notice"],
            "tool arguments approval must be visible in history")
    require("L7 已确认" in operation["description"] and "L7 已确认" in review["notice"],
            "tool result array approval must be visible in history")
    require("L8 已确认" in operation["description"] and "L8 已确认" in review["notice"],
            "text-only tool result approval must be visible in history")
    require("L9 已确认" in operation["description"] and "L9 已确认" in review["notice"],
            "Mate Runtime wrapper approval must be visible in history")
    require("L10 已确认" in operation["description"] and "L10 已确认" in review["notice"],
            "tool result boolean outcome approval must be visible in history")
    for clause in ("普通分页已确认", "不再固定快照", "跨页保持相同 limit", "不按 createdAt 重排",
                   "每页读取该次查询可见的当前分支完整事件", "本接口不承诺自动检测跨页变化",
                   "允许 Session running 时查询", "nextPage=null 仅表示本次查询没有下一页",
                   "省略 limit 时返回最多 50 条，允许 1～200", "result 只含 events 和 nextPage，不返回 total",
                   "L4 已确认：页码合法但超出当前记录范围时返回 200，events=[]、nextPage=null",
                   "不掩盖非法参数或读取失败",
                   "不能用某条历史 idle 判定现在可提交 M2",
                   "每页重新检查访问边界", "配置变更、压缩、Usage", "B01～B15 已确认"):
        require(clause in operation["description"], f"missing visible history boundary: {clause}")
    complete = complete_streams(post)
    expected = {
        "200-first-page": complete["200-message"][:2],
        "200-next-page": complete["200-message"][2:],
        "200-confirmation": complete["200-confirming"] + complete["200-tool-confirmation"],
        "200-interrupted": complete["200-message-interrupted"][:-1] + complete["200-interrupt"],
        "200-empty": [],
        "200-out-of-range": [],
        "200-tool-success": complete["200-tool-success"],
        "200-todo-updated": complete["200-todo-updated"],
        "200-execution-failed": complete["200-execution-failed"],
        "200-plan-approved": complete["200-plan-review"] + complete["200-plan-approved"],
        "200-plan-revised": complete["200-plan-review"] + complete["200-plan-revised"],
        "200-question-answered": complete["200-question-asking"] + complete["200-question-answered"],
        "200-skill-message": complete_streams(json.loads((ROOT / "接口契约/操作/13-execute-session-command.json").read_text()))["200-skill-message"],
    }
    results, all_types, errors = {}, set(), set()
    ids = [x["id"] for x in operation["responses"]]
    require(len(ids) == len(set(ids)), "duplicate history response IDs")
    for response in operation["responses"]:
        require(response["headers"]["Content-Type"] == "application/json"
                and response["headers"]["Cache-Control"] == "no-store", "history is uncached JSON")
        for body in response["bodies"].values():
            validate_public_payload(body)
            if response["status"] != "200":
                require(set(body) == {"resCode", "resMsg"}, "history error must omit result")
                errors.add((response["status"], body["resCode"]))
                continue
            require(set(body) == {"resCode", "resMsg", "result"} and body["resCode"] == "0"
                    and body["resMsg"] == "success", "history success uses ResultBean")
            result = body["result"]
            require(set(result) == {"events", "nextPage"}, "unexpected history page fields")
            require(result["nextPage"] is None or
                    (type(result["nextPage"]) is int and result["nextPage"] >= 1),
                    "nextPage must be a positive JSON integer or null, never a string or boolean")
            if response["id"] != "200-configuration":
                require(result["events"] == expected[response["id"]], "history complete records drift from POST frames")
            else:
                require([e["type"] for e in result["events"]] == ["session.model_changed", "session.thinking_changed", "session.mode_changed", "session.compacted"], "configuration projection coverage")
            seen = set()
            for event in result["events"]:
                validate_frame(event, receipt=event["type"].startswith("user."), history=True)
                require(event.get("phase") != "delta", "delta must not enter history")
                require(event["eventId"] not in seen, "duplicate history event, including shared idle")
                seen.add(event["eventId"])
                all_types.add(event["type"])
            results[response["id"]] = result
    require(set(results) == set(expected) | {"200-configuration"}, "missing paired page, confirmation, interrupt or empty examples")
    require(all_types == USER_EVENT_TYPES | STREAM_TYPES | HISTORY_TYPES, "missing complete event type")
    require(results["200-first-page"]["nextPage"] == 2, "page 1 must continue at page 2")
    require(all(query in operation["requestBody"]["description"]
                for query in ("?page=1&limit=2", "?page=2&limit=2")), "paired numeric requests required")
    require(all(x["nextPage"] is None for key, x in results.items() if key != "200-first-page"),
            "example page exhaustion must return null")
    require(errors == {("400", "INVALID_SESSION_ID"), ("400", "INVALID_EVENT_LIST_QUERY"),
                       ("404", "SESSION_NOT_FOUND"), ("500", "EVENT_LIST_FAILED"), ("503", "EVENT_SERVICE_UNAVAILABLE")}, "history error catalog drift")


def validate_history_regressions(model: dict, post: dict) -> int:
    edits = [
        lambda m: m["operation"].update(path="/sessions/{sessionId}/events/stream"),
        lambda m: m["operation"]["requestBody"].update(required=True),
        lambda m: m["operation"]["requestHeaderExamples"][0]["headers"].append(
            {"name": "access-token", "value": "opaque-access-token", "required": True}),
        lambda m: m["review"].update(confirmedChoices={}),
        lambda m: m["review"]["confirmedChoices"].update(**{"L2-page-size": "A-default100-max200"}),
        lambda m: m["review"]["confirmedChoices"].update(**{"L3-page-metadata": "B-include-total"}),
        lambda m: m["review"]["confirmedChoices"].update(**{"L4-out-of-range-page": "B-query-error"}),
        lambda m: m["review"]["confirmedChoices"].update(**{"L5-agent-message-content": "B-content-blocks"}),
        lambda m: m["review"]["confirmedChoices"].update(**{"L6-tool-call-arguments": "B-json-string"}),
        lambda m: m["review"]["confirmedChoices"].update(**{"L7-tool-result-content": "B-string"}),
        lambda m: m["review"]["confirmedChoices"].update(**{"L8-tool-result-types": "B-mixed-types"}),
        lambda m: m["review"]["confirmedChoices"].update(**{"L9-mate-tool-identity": "B-business-tool"}),
        lambda m: m["review"]["confirmedChoices"].update(**{"L10-tool-result-outcome": "B-status-enum"}),
        lambda m: m["review"]["confirmedPagination"].update(outOfRangePage="query-error"),
        lambda m: m["review"]["historyProposal"].update(outOfRangePage="empty-success"),
        lambda m: m["review"]["confirmedPagination"].update(defaultLimit=100),
        lambda m: m["review"]["confirmedPagination"].update(maxLimit=500),
        lambda m: m["review"]["confirmedPagination"]["responseFields"].append("total"),
        lambda m: m["operation"]["parameters"][1].update(schema="integer 1..200; default 100"),
        lambda m: m["review"].update(pendingReview=["whole approval"]),
        lambda m: m["review"]["inheritedRules"].update(deltaHistory=True),
        lambda m: m["review"]["confirmedPagination"].update(fixedSnapshot=True),
        lambda m: m["review"]["confirmedPagination"].update(cursorEncryption=True),
        lambda m: m["review"]["confirmedPagination"].update(readWhileRunning=False),
        lambda m: m["review"]["confirmedPagination"].update(sameLimitAcrossPages=False),
        lambda m: m["review"]["historyProposal"].update(cursorBindings=["branch", "committedUpperBound"]),
        lambda m: m["review"]["historyProposal"].update(cursorTtlSeconds=3600),
        lambda m: m["review"]["questions"].append({"id": "L1-page-direction"}),
        lambda m: m["review"]["questions"].append({"id": "L2-page-size"}),
        lambda m: m["review"]["questions"].append({"id": "L3-page-metadata"}),
        lambda m: m["review"]["questions"].append({"id": "L4-out-of-range-page"}),
        lambda m: m["review"]["questions"].append({"id": "L5-agent-message-content"}),
        lambda m: m["review"]["questions"].append({"id": "L6-tool-call-arguments"}),
        lambda m: m["review"]["questions"].append({"id": "L7-tool-result-content"}),
        lambda m: m["review"]["questions"].append({"id": "L8-tool-result-types"}),
        lambda m: m["review"]["questions"].append({"id": "L9-mate-tool-identity"}),
        lambda m: m["review"]["questions"].append({"id": "L10-tool-result-outcome"}),
        lambda m: m["review"]["batchReview"].update(status="proposal"),
        lambda m: next(x for x in m["operation"]["responses"] if x["id"] == "200-out-of-range").update(status="204"),
        lambda m: next(x for x in m["operation"]["responses"] if x["id"] == "200-out-of-range")
                ["bodies"]["default"]["result"].update(events=None),
        lambda m: m["operation"]["parameters"][2].update(schema="opaque string"),
        lambda m: m["operation"]["parameters"].append({"in": "query", "name": "snapshotId"}),
        lambda m: m["operation"]["responses"][0]["bodies"]["default"]["result"].update(nextPage=None),
        lambda m: m["operation"]["responses"][0]["bodies"]["default"]["result"].update(nextPage="2"),
        lambda m: m["operation"]["responses"][0]["bodies"]["default"]["result"].update(nextPage=True),
        lambda m: m["operation"]["responses"][0]["bodies"]["default"]["result"].update(nextPage=0),
        lambda m: m["operation"]["responses"][0]["bodies"]["default"]["result"].update(nextPage=3),
        lambda m: m["operation"]["responses"][0]["bodies"]["default"]["result"].update(total=3),
        lambda m: m["operation"]["responses"][0]["bodies"]["default"]["result"].update(snapshotId="snapshot-demo"),
        lambda m: m["operation"]["responses"][1]["bodies"]["default"]["result"].update(nextPage="page_more"),
        lambda m: m["operation"]["responses"][0]["bodies"]["default"]["result"]["events"][0].update(entrySeq=1),
        lambda m: m["operation"]["responses"][0]["bodies"]["default"]["result"]["events"][1].update(phase="delta"),
        lambda m: m["operation"]["responses"][0]["bodies"]["default"]["result"]["events"][1].update(content="drift"),
        lambda m: m["operation"]["responses"][2]["bodies"]["default"]["result"]["events"].reverse(),
        lambda m: m["operation"]["responses"][3]["bodies"]["default"]["result"]["events"].append(
            m["operation"]["responses"][3]["bodies"]["default"]["result"]["events"][-1]),
        lambda m: m["operation"]["responses"][-1]["bodies"]["zh-CN"].update(result=None),
        lambda m: m["operation"].update(description=m["operation"]["description"].replace(
            "不能用某条历史 idle 判定现在可提交 M2", "历史 idle 允许新消息")),
    ]
    for index, edit in enumerate(edits):
        candidate = copy.deepcopy(model)
        edit(candidate)
        try:
            validate_history_model(candidate, post)
        except (KeyError, ValueError):
            continue
        raise ValueError(f"negative history regression accepted: {index}")
    return len(edits)


def validate_review_pages(post: dict) -> None:
    spec = importlib.util.spec_from_file_location("runtime_contract_validator", ROOT / "validate-chat-http-v1.py")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    history_source = (ROOT / "chat-api-review.html").read_text(encoding="utf-8")
    history_parser = validator.ContractHtmlParser()
    history_parser.feed(history_source)
    histories, history_scripts = validator.parse_generated_models(history_parser)
    require(len(histories) == history_parser.static_review_count == 10 and len(history_scripts) == 1,
            "show one unified catalog")
    history = next(model for model in histories if model["operation"]["operationKey"] == "listSessionEvents")
    validate_history_model(history, post)
    validator.validate_executable_script(history_scripts[0])
    visible_history = " ".join(history_parser.visible_text)
    for text in ("作用", "调用上下文 Header", "参数与请求体", "响应", "普通分页", "下一页", "确认与续跑历史",
                 "中断历史", "已确认目标契约", "默认 50、上限 200 已确认", "不返回 total", "L4 已确认"):
        require(text in visible_history, f"no-JavaScript history page missing {text}")
    require(all(f'data-question-id="{key}"' not in history_source
                for key in ("L1-page-direction", "L2-page-size", "L3-page-metadata", "L4-out-of-range-page",
                            "L5-agent-message-content", "L6-tool-call-arguments", "L7-tool-result-content",
                            "L8-tool-result-types", "L8-mate-result-projection", "L9-mate-tool-identity",
                            "L10-tool-result-outcome")),
            "do not reopen confirmed choices")
    require("data-label" in history_source and "max-width: 680px" in history_source, "history responsive rules missing")
    source = history_source
    parser = validator.ContractHtmlParser()
    parser.feed(source)
    models, scripts = validator.parse_generated_models(parser)
    require(len(models) == parser.static_review_count == 10 and len(scripts) == 1, "show one unified catalog")
    merged = next(model for model in models if model["operation"]["operationKey"] == "submitSessionEvent")
    validate_model(merged)
    validator.validate_executable_script(scripts[0])
    visible = " ".join(parser.visible_text)
    for text in ("作用", "调用上下文 Header", "参数与请求体", "响应", "首个业务帧", "已确认目标契约",
                 "结束规则已确认", "等待工具确认时也关闭", "中断推送分工已确认", "数据库中断机制已确认",
                 "中断查询优化已确认", "先登记等待再补读已提交终态", "同一终态每条响应最多投递一次"):
        require(text in visible, f"no-JavaScript page is missing {text}")
    require('data-question-id="' not in source, "confirmed decisions must not leave another approval form")
    require("data-label" in source and "max-width: 680px" in source, "responsive rules missing")


def validate_display_name_regressions(post: dict) -> None:
    calls = [event for events in complete_streams(post).values() for event in events
             if event["type"] == "agent.tool_call"]
    require(any(event["toolName"] != "CallMateTool" for event in calls), "include framework label examples")
    require(any(event["toolName"] == "CallMateTool" for event in calls), "include business display names")
    call = next(event for event in calls if event["toolName"] == "CallMateTool")
    require(call.get("displayName") == "隔离园区端口", "business metadata example missing")
    unnamed = {key: value for key, value in call.items() if key != "displayName"}
    validate_frame(unnamed)
    validate_frame(unnamed, history=True)
    for value in (None, "", "  ", " 名称 ", 42, False, {}):
        for history in (False, True):
            try:
                validate_frame({**unnamed, "displayName": value}, history=history)
            except ValueError:
                continue
            raise ValueError("producer must omit invalid displayName; UI tolerance is a separate boundary")
    try:
        validate_frame({**call, "label": "duplicate"})
    except ValueError:
        return
    raise ValueError("synonymous label must not be published")


def validate_batch_field_regressions(post: dict, history: dict) -> int:
    streams = complete_streams(post)
    call = next(e for e in streams["200-confirming"] if e["type"] == "agent.tool_call")
    failure = next(e for e in streams["200-tool-confirmation"] if e["type"] == "agent.tool_result")
    success = next(e for e in streams["200-tool-success"] if e["type"] == "agent.tool_result")
    idle = streams["200-execution-failed"][-1]
    config = next(r for r in history["operation"]["responses"] if r["id"] == "200-configuration")["bodies"]["default"]["result"]["events"]
    cases = [
        (call, lambda e: e.pop("sourceEventId")),
        (call, lambda e: e.pop("requiresConfirmation")),
        (call, lambda e: e.update(requiresConfirmation="false")),
        (call, lambda e: e.update(createdAt="2026-09-08T00:00:00Z")),
        (failure, lambda e: e.pop("errorCode")),
        (failure, lambda e: e.update(errorCode="RAW_MATE_ERROR")),
        (success, lambda e: e.update(errorCode="TOOL_EXECUTION_FAILED")),
        (success, lambda e: e.update(content=[])),
        (idle, lambda e: e.pop("message")),
        (idle, lambda e: e.update(reason="done")),
        (config[0], lambda e: e.update(reason="model_changed")),
        (config[0], lambda e: e.update(sourceEventId="unrelated")),
        (config[1], lambda e: e.update(thinking="false")),
        (config[2], lambda e: e.update(summary="private")),
        (config[2], lambda e: e.update(reason="threshold")),
    ]
    for event, edit in cases:
        changed = copy.deepcopy(event)
        edit(changed)
        try:
            validate_frame(changed, history=True)
        except ValueError:
            continue
        raise ValueError(f"batch field regression accepted: {changed}")
    skill = json.loads((ROOT / "接口契约/操作/13-execute-session-command.json").read_text())
    frames = complete_streams(skill)["200-skill-message"]
    request = next(e["value"] for e in skill["operation"]["requestBody"]["examples"] if e["value"]["name"] == "skill:pdf")
    content = [{"type": "text", "text": "/" + request["name"] + " " + request["arguments"]}]
    content += [{"type": "file", "fileId": v} for v in request["fileIds"]]
    require(frames[0]["type"] == "user.message" and frames[0]["content"] == content, "Skill receipt must preserve original invocation and files")
    require(all(e["sourceEventId"] == frames[0]["eventId"] for e in frames[1:]), "Skill shares original root identity")
    require(frames[-1]["type"] == "session.status_idle" and frames[-1]["reason"] == "done", "Skill example ends normally")
    return len(cases)


def validate_todo_regressions(post: dict) -> int:
    frames = complete_streams(post)["200-todo-updated"]
    updates = [e for e in frames if e["type"] == "agent.todo_updated"]
    require(len(updates) == 2, "example must demonstrate replacement snapshots")
    for index, event in enumerate(frames):
        if event["type"] != "agent.todo_updated":
            continue
        result = frames[index - 1]
        require(result["type"] == "agent.tool_result" and result["isError"] is False
                and result["toolCallId"] == event["toolCallId"], "task event follows the matching successful result")
        require(json.loads(result["content"][0]["text"])["todos"] == event["todos"],
                "tool result and public task snapshot must have one source")
    empty = copy.deepcopy(updates[0])
    empty["todos"] = []
    validate_frame(empty)
    edits = [
        lambda e: e.pop("todos"), lambda e: e.update(todos=None),
        lambda e: e.update(todos="[]"), lambda e: e.update(phase="delta"),
        lambda e: e.pop("sourceEventId"), lambda e: e.update(toolCallId=""),
        lambda e: e["todos"][0].update(status="done"),
        lambda e: e["todos"][0].update(content=" "),
        lambda e: e["todos"][0].update(content=" padded"),
        lambda e: e["todos"][0].update(content="a" * 1025),
        lambda e: e["todos"][0].update(content="😀" * 513),
        lambda e: e["todos"][0].update(priority="high"),
        lambda e: e["todos"].append(copy.deepcopy(e["todos"][0])),
        lambda e: e["todos"][0].update(status="in_progress"),
        lambda e: e.update(todos=[dict(content=str(i), status="pending") for i in range(101)]),
    ]
    for edit in edits:
        candidate = copy.deepcopy(updates[0])
        edit(candidate)
        try:
            validate_frame(candidate)
        except ValueError:
            continue
        raise ValueError("invalid task snapshot accepted")
    return len(edits)


def validate_plan_flow(post: dict) -> None:
    streams = complete_streams(post)
    review, approved, revised = (streams[name] for name in
                                 ("200-plan-review", "200-plan-approved", "200-plan-revised"))
    plans = [event for event in review if event["type"] == "agent.plan"]
    require(len(plans) == 1, "review publishes one complete proposal")
    plan = plans[0]
    calls = [event for event in review if event.get("toolName") == "ExitPlanMode"]
    require(len(calls) == 1 and calls[0]["toolCallId"] == plan["toolCallId"]
            and calls[0]["arguments"] == {"plan": plan["content"]}, "proposal must preserve exact ExitPlanMode input")
    require(review[-1]["reason"] == "confirming", "review closes with a confirming wait")
    require(not any(event["type"] == "agent.todo_updated" or event.get("toolName") == "TodoUpdate"
                    or event["type"] == "agent.tool_result" and event["toolCallId"] == plan["toolCallId"]
                    for event in review), "research must not publish execution progress or early ExitPlanMode result")
    for frames, decision in ((approved, "approve"), (revised, "revise")):
        receipt = frames[0]
        require(receipt["type"] == "user.plan_confirmation" and receipt["result"] == decision
                and receipt["targetEventId"] == plan["eventId"], "decision must target the reviewed proposal")
        result = next(event for event in frames if event["type"] == "agent.tool_result")
        require(result["toolCallId"] == plan["toolCallId"] and result["isError"] is False,
                "decision completes the original ExitPlanMode normally")
        structured = json.loads(result["content"][0]["text"].split("\n", 1)[0])
        require(structured["approved"] is (decision == "approve"), "tool decision and user decision differ")
    mode = approved[1]
    require(mode["type"] == "session.mode_changed" and mode["confirmationEventId"] == approved[0]["eventId"]
            and mode["sourceEventId"] == review[0]["eventId"], "approval receipt must precede its bound mode change")
    require(approved[2]["type"] == "agent.tool_result", "approved mode change precedes ExitPlanMode result")
    updates = [event for event in approved if event["type"] == "agent.todo_updated"]
    require(len(updates) == 3 and all(todo["status"] == "completed" for todo in updates[-1]["todos"]),
            "execution example must demonstrate task completion")
    for index, event in enumerate(approved):
        if event["type"] == "agent.todo_updated":
            result = approved[index - 1]
            require(result["type"] == "agent.tool_result" and result["isError"] is False
                    and result["toolCallId"] == event["toolCallId"]
                    and json.loads(result["content"][0]["text"])["todos"] == event["todos"],
                    "task event must match the finalized result")
    new_plan = next(event for event in revised if event["type"] == "agent.plan")
    require(new_plan["eventId"] != plan["eventId"] and revised[-1]["reason"] == "confirming",
            "revision publishes a new proposal and waits again")
    require(not any(event["type"] in {"session.mode_changed", "agent.todo_updated"}
                    or event.get("toolName") == "TodoUpdate" for event in revised),
            "revision stays in plan without execution progress")


def validate_plan_regressions(post: dict) -> int:
    validate_plan_flow(post)
    streams = complete_streams(post)
    plan = next(event for event in streams["200-plan-review"] if event["type"] == "agent.plan")
    approve = streams["200-plan-approved"][0]
    revise = streams["200-plan-revised"][0]
    mode = streams["200-plan-approved"][1]
    cases = [
        (plan, lambda e: e.update(content="no heading")),
        (plan, lambda e: e.update(content="# " + "a" * 262143)),
        (plan, lambda e: e.update(content="# " + "😀" * 131072)),
        (plan, lambda e: e.update(content=None)),
        (plan, lambda e: e.update(phase="completed")),
        (plan, lambda e: e.pop("toolCallId")),
        (plan, lambda e: e.pop("sourceEventId")),
        (approve, lambda e: e.update(feedback=None)),
        (approve, lambda e: e.update(result="accept")),
        (approve, lambda e: e.update(result={})),
        (approve, lambda e: e.update(result=None)),
        (approve, lambda e: e.update(targetEventId=" ")),
        (approve, lambda e: e.update(targetEventId="a" * 129)),
        (approve, lambda e: e.update(planId="unregistered")),
        (revise, lambda e: e.update(feedback=None)),
        (revise, lambda e: e.update(feedback="\t")),
        (revise, lambda e: e.update(feedback=12)),
        (revise, lambda e: e.update(feedback="😀" * 2049)),
        (mode, lambda e: e.pop("confirmationEventId")),
        (mode, lambda e: e.pop("sourceEventId")),
        (mode, lambda e: e.update(previousMode="build", mode="plan")),
        (mode, lambda e: e.update(reason="requested")),
    ]
    for event, edit in cases:
        candidate = copy.deepcopy(event)
        edit(candidate)
        try:
            validate_frame(candidate, receipt=candidate["type"].startswith("user."))
        except (KeyError, ValueError):
            continue
        raise ValueError("invalid plan review event accepted")
    flow_cases = [
        ("200-plan-review", "agent.plan", lambda e: e.update(content="# Another proposal")),
        ("200-plan-approved", "user.plan_confirmation", lambda e: e.update(targetEventId="stale-plan")),
        ("200-plan-approved", "session.mode_changed", lambda e: e.update(confirmationEventId="wrong-receipt")),
        ("200-plan-revised", "agent.plan", lambda e: e.update(eventId=plan["eventId"])),
    ]
    for response_id, event_type, edit in flow_cases:
        candidate = copy.deepcopy(post)
        response = next(item for item in candidate["operation"]["responses"] if item["id"] == response_id)
        frames = parse_stream(response["bodies"]["default"])
        edit(next(event for event in frames if event["type"] == event_type))
        response["bodies"]["default"] = "".join("data: " + json.dumps(event, ensure_ascii=False) + "\n\n"
                                                for event in frames)
        try:
            validate_plan_flow(candidate)
        except ValueError:
            continue
        raise ValueError("invalid plan review causal link accepted")
    # Provider tool call identities retain the existing contract without a 128-unit limit.
    long_tool_identity = dict(plan, toolCallId="provider-call-" + "x" * 200)
    validate_frame(long_tool_identity)
    without_feedback = copy.deepcopy(revise)
    without_feedback.pop("feedback")
    validate_frame(without_feedback, receipt=True)
    request = {key: value for key, value in approve.items() if key not in {"eventId", "createdAt"}}
    validate_plan_confirmation(request)
    malformed_request = dict(request, feedback="not allowed")
    try:
        validate_plan_confirmation(malformed_request)
    except ValueError:
        return len(cases) + len(flow_cases) + 1
    raise ValueError("approve request accepted feedback")


def main() -> int:
    try:
        common = json.loads(COMMON_PATH.read_text(encoding="utf-8"))
        model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
        history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        require(common["reviewState"] == {"currentOperation": "listSessionEvents", "confirmedOperations": ["submitSessionEvent", "listSessionEvents"], "reviewMode": "completed", "semanticBatch": "2026-09-08.1-confirmed"}, "target contracts ready after confirmed batch")
        require(common["eventContract"]["detailStatus"] == "implementation-ready", "no extra review gate")
        require(sorted(MODEL_PATH.parent.glob("*.json")) == [MODEL_PATH, HISTORY_PATH],
                "only POST and GET history remain active, not the retired stream")
        validate_model(model)
        negative_count = validate_negative_regressions(model)
        validate_history_model(history, model)
        history_count = validate_history_regressions(history, model)
        validate_display_name_regressions(model)
        batch_count = validate_batch_field_regressions(model, history)
        todo_count = validate_todo_regressions(model)
        plan_count = validate_plan_regressions(model)
        question_count = validate_question_regressions(model)
        require(set(common["eventContract"]["completeTypes"]) == USER_EVENT_TYPES | STREAM_TYPES | HISTORY_TYPES,
                "shared complete event catalog differs from validated types")
        subprocess.run([sys.executable, str(ROOT / "render_chat_api.py"), "--check"], check=True)
        validate_review_pages(model)
    except (KeyError, OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"error: {error}")
        return 2
    print(f"POST SSE and ListEvents contracts valid; {negative_count} POST and {history_count} history and {batch_count} batch field and {todo_count} task snapshot and {plan_count} plan review and {question_count} question negative regressions rejected")
    print("Static contract validation only; database pagination and runtime concurrency were not executed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

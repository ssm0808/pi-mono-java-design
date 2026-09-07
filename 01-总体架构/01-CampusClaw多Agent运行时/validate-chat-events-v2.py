#!/usr/bin/env python3
"""Validate POST SSE and ListEvents models, examples and generated review pages."""

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
HISTORY_PATH = ROOT / "接口契约-v2" / "操作" / "02-list-session-events.json"
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
    "M8-control-retirement": "remove-standalone-controls-follow-up-future-only",
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


def complete_streams(post: dict) -> dict:
    return {item["id"]: [event for event in parse_stream(item["bodies"]["default"])
                         if event.get("phase") != "delta"]
            for item in post["operation"]["responses"] if item["status"] == "200"}


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
        "scope": "current-branch-per-request", "thinkingFilter": "session-policy",
        "readToolToken": False,
    }, "keep only the remaining candidates, not cursor keys, bindings or expiry")
    require(review["confirmedChoices"] == {
        "L1-page-direction": "A-oldest-first", "L1-page-format": "one-based-integer",
        "L1-consistency": "no-fixed-snapshot",
        "L2-page-size": "B-default50-max200", "L3-page-metadata": "A-events-nextPage-only",
        "L4-out-of-range-page": "A-empty-success",
    } and "ListEvents 接口整体确认" in review["pendingReview"],
            "pagination is approved, not the whole history operation")
    require(review["questions"] == [], "L1-L4 are confirmed; do not reopen pagination choices")
    for clause in ("普通分页已确认", "不再固定快照", "跨页保持相同 limit", "不按 createdAt 重排",
                   "每页读取该次查询可见的当前分支完整事件", "本接口不承诺自动检测跨页变化",
                   "允许 Session running 时查询", "nextPage=null 仅表示本次查询没有下一页",
                   "省略 limit 时返回最多 50 条，允许 1～200", "result 只含 events 和 nextPage，不返回 total",
                   "L4 已确认：页码合法但超出当前记录范围时返回 200，events=[]、nextPage=null",
                   "不掩盖非法参数或读取失败",
                   "不能用某条历史 idle 判定现在可提交 M2",
                   "每页重新检查访问边界", "配置变更、压缩、Usage", "未整体确认 ListEvents 或合并 POST"):
        require(clause in operation["description"], f"missing visible history boundary: {clause}")
    complete = complete_streams(post)
    expected = {
        "200-first-page": complete["200-message"][:2],
        "200-next-page": complete["200-message"][2:],
        "200-confirmation": complete["200-confirming"] + complete["200-tool-confirmation"],
        "200-interrupted": complete["200-message-interrupted"][:-1] + complete["200-interrupt"],
        "200-empty": [],
        "200-out-of-range": [],
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
            require(result["events"] == expected[response["id"]], "history complete records drift from POST frames")
            seen = set()
            for event in result["events"]:
                validate_frame(event, receipt=event["type"].startswith("user."))
                require(event.get("phase") != "delta", "delta must not enter history")
                require(event["eventId"] not in seen, "duplicate history event, including shared idle")
                seen.add(event["eventId"])
                all_types.add(event["type"])
            results[response["id"]] = result
    require(set(results) == set(expected), "missing paired page, confirmation, interrupt or empty examples")
    require(all_types == USER_EVENT_TYPES | STREAM_TYPES, "missing complete event type")
    require(results["200-first-page"]["nextPage"] == 2, "page 1 must continue at page 2")
    require(all(query in operation["requestBody"]["description"]
                for query in ("?page=1&limit=2", "?page=2&limit=2")), "paired numeric requests required")
    require(all(x["nextPage"] is None for key, x in results.items() if key != "200-first-page"),
            "example page exhaustion must return null")
    require(errors == {("400", "INVALID_SESSION_ID"), ("400", "INVALID_EVENT_LIST_QUERY"),
                       ("404", "SESSION_NOT_FOUND"), ("500", "EVENT_LIST_FAILED")}, "history error catalog drift")


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
        lambda m: m["review"]["confirmedPagination"].update(outOfRangePage="query-error"),
        lambda m: m["review"]["historyProposal"].update(outOfRangePage="empty-success"),
        lambda m: m["review"]["confirmedPagination"].update(defaultLimit=100),
        lambda m: m["review"]["confirmedPagination"].update(maxLimit=500),
        lambda m: m["review"]["confirmedPagination"]["responseFields"].append("total"),
        lambda m: m["operation"]["parameters"][1].update(schema="integer 1..200; default 100"),
        lambda m: m["review"].update(pendingReview=[]),
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
                 "中断历史", "未整体确认", "默认 50、上限 200 已确认", "不返回 total", "L4 已确认"):
        require(text in visible_history, f"no-JavaScript history page missing {text}")
    require(all(f'data-question-id="{key}"' not in history_source
                for key in ("L1-page-direction", "L2-page-size", "L3-page-metadata", "L4-out-of-range-page")),
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
    for text in ("作用", "调用上下文 Header", "参数与请求体", "响应", "首个业务帧", "未整体确认合并接口",
                 "结束规则已确认", "等待工具确认时也关闭", "中断推送分工已确认", "数据库中断机制已确认",
                 "中断查询优化已确认", "先登记等待再补读已提交终态", "同一终态每条响应最多投递一次"):
        require(text in visible, f"no-JavaScript page is missing {text}")
    require("data-question-id=" not in source, "confirmed receipt must not remain a question")
    require("data-label" in source and "max-width: 680px" in source, "responsive rules missing")


def main() -> int:
    try:
        common = json.loads(COMMON_PATH.read_text(encoding="utf-8"))
        model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
        history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        require(common["reviewState"] == {"currentOperation": "listSessionEvents", "confirmedOperations": []},
                "history is current; neither operation is fully approved")
        require(sorted(MODEL_PATH.parent.glob("*.json")) == [MODEL_PATH, HISTORY_PATH],
                "only POST and GET history remain active, not the retired stream")
        validate_model(model)
        negative_count = validate_negative_regressions(model)
        validate_history_model(history, model)
        history_count = validate_history_regressions(history, model)
        subprocess.run([sys.executable, str(ROOT / "render_chat_api.py"), "--check"], check=True)
        validate_review_pages(model)
    except (KeyError, OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"error: {error}")
        return 2
    print(f"POST SSE and ListEvents contracts valid; {negative_count} POST and {history_count} history negative regressions rejected")
    print("Static contract validation only; database pagination and runtime concurrency were not executed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

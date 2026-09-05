#!/usr/bin/env python3
"""Render the current operation and retire superseded whole-operation approval."""

import argparse
from pathlib import Path

import render_chat_http_v1 as renderer


ROOT = Path(__file__).resolve().parent
CURRENT_OUTPUT = ROOT / "chat-events-v2-review.html"
CONFIRMED_OUTPUT = ROOT / "chat-events-v2-confirmed.html"


def build_html(confirmed: bool = False) -> str:
    settings = {
        "CONTRACT_ROOT": ROOT / "接口契约-v2",
        "COMMON_PATH": ROOT / "接口契约-v2" / "common.json",
        "OPERATIONS_ROOT": ROOT / "接口契约-v2" / "操作",
    }
    previous = {key: getattr(renderer, key) for key in settings}
    original_loader = renderer.load_contract
    try:
        for key, value in settings.items():
            setattr(renderer, key, value)
        common, models = original_loader()
        state = common["reviewState"]
        keys = state["confirmedOperations"] if confirmed else [state["currentOperation"]]
        if confirmed and not keys:
            return '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Session Events v2 — 评审状态更新</title></head>
<body><main><h1>原独立 POST JSON 方案已被合并方案替代</h1>
<p>当前没有整体确认的 v2 接口。既有请求、Header、eventId、排序和类型决定继续有效；
完整本次 user.* 首帧回执、对应 idle 关闭（含等待工具确认）、中断推送分工、数据库中断机制及单消息准入已确认；数据库控制细节、周期、故障与其他字段仍在评审。</p>
<p><a href="chat-events-v2-review.html">打开当前 POST 合并接口评审</a></p>
<p>旧方案可从 Git 历史恢复，不再作为现行接口展示。</p></main></body></html>
'''
        selected = [model for model in models if model["operation"]["operationKey"] in keys]
        renderer.require(len(selected) == len(keys) and bool(keys), "Review operation selection is invalid")
        for model in selected:
            model["api"]["visibility"] = (
                "Internal · 已确认接口 · target-only" if confirmed
                else "Internal · 当前评审：POST 提交与推送合并 · target-only"
            )
        renderer.load_contract = lambda: (common, selected)
        return renderer.build_html()
    finally:
        renderer.load_contract = original_loader
        for key, value in previous.items():
            setattr(renderer, key, value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        for destination, confirmed in ((CURRENT_OUTPUT, False), (CONFIRMED_OUTPUT, True)):
            content = build_html(confirmed)
            if args.check:
                renderer.require(destination.read_text(encoding="utf-8") == content,
                                 f"Generated HTML is out of date: {destination.name}")
            else:
                renderer.write_output(destination, content)
            print(destination)
    except (OSError, KeyError, ValueError) as error:
        print(f"error: {error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Render the source-first mate-service Chat Command contract as standalone HTML."""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import tempfile
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = ROOT.parents[1]
RUNTIME_ROOT = REPOSITORY_ROOT / "01-总体架构" / "01-CampusClaw多Agent运行时"
RUNTIME_RENDERER = RUNTIME_ROOT / "render_chat_http_v1.py"
CONTRACT_ROOT = ROOT / "接口契约"
DEFAULT_OUTPUT = ROOT / "chat-command-v1-review.html"

BUSINESS_CSS = r"""
.review-guide {
  margin-block-end: 16px;
  padding: 18px;
  border: 1px solid light-dark(#d8dee6, #37414d);
  border-radius: 12px;
  background: light-dark(#ffffff, #1a2028);
  color: light-dark(#17202a, #edf2f7);
  font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.review-guide h1,
.review-guide p { margin: 0; }
.review-guide h1 { font-size: 20px; font-weight: 600; }
.review-guide p { margin-top: 8px; line-height: 1.6; }
.review-guide-steps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 14px;
}
.review-guide-step,
.company-api-review .business-step,
.company-api-review .business-scenario {
  padding: 12px;
  border: 1px solid light-dark(#d8dee6, #37414d);
  border-radius: 8px;
  background: light-dark(#f7f8fa, #11151b);
}
.review-guide-step strong,
.company-api-review .business-step strong { display: block; margin-bottom: 5px; }
.company-api-review .business-surface {
  overflow: hidden;
  border: 1px solid light-dark(#0969da, #58a6ff);
  border-radius: 12px;
  background: light-dark(#ffffff, #1a2028);
}
.company-api-review .business-head {
  padding: 16px;
  border-bottom: 1px solid light-dark(#d8dee6, #37414d);
  background: light-dark(#eaf3ff, #132b46);
}
.company-api-review .business-head h2 { margin-top: 8px; }
.company-api-review .business-badge {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 999px;
  background: light-dark(#0969da, #58a6ff);
  color: #ffffff;
  font-size: 12px;
}
.company-api-review .business-summary { margin-top: 8px; line-height: 1.6; }
.company-api-review .business-section {
  padding: 16px;
  border-bottom: 1px solid light-dark(#d8dee6, #37414d);
}
.company-api-review .business-section:last-child { border-bottom: 0; }
.company-api-review .business-flow,
.company-api-review .business-scenarios {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 10px;
}
.company-api-review .business-step span,
.company-api-review .business-scenario p,
.company-api-review .business-scenario li { font-size: 13px; line-height: 1.55; }
.company-api-review .business-step > span { display: block; }
.company-api-review .business-step > .muted,
.company-api-review .business-scenario > .muted { margin-top: 8px; }
.company-api-review .business-scenario h4 { margin: 0 0 8px; font-size: 14px; }
.company-api-review .business-scenario ol { margin: 0; padding-left: 20px; }
.company-api-review .business-note {
  padding: 11px 12px;
  border-left: 4px solid light-dark(#0969da, #58a6ff);
  background: light-dark(#f2f7ff, #132b46);
  font-size: 13px;
  line-height: 1.6;
}
.company-api-review .exact-contract {
  margin-top: 12px;
  padding: 12px;
  border: 1px dashed light-dark(#8c959f, #6e7681);
  border-radius: 10px;
}
.company-api-review .exact-contract > summary { font-size: 14px; }
.company-api-review .exact-contract .api-shell { margin-top: 12px; }
@media (max-width: 680px) {
  .review-guide-steps,
  .company-api-review .business-flow,
  .company-api-review .business-scenarios { grid-template-columns: 1fr; }
}
"""


def load_runtime_renderer() -> Any:
    spec = importlib.util.spec_from_file_location("runtime_contract_renderer", RUNTIME_RENDERER)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load the shared Runtime contract renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SHARED = load_runtime_renderer()


def render_page_guide() -> str:
    return (
        '<section class="review-guide">'
        '<h1>mate-service Chat Command API 评审页</h1>'
        '<p>默认内容用于产品、前端和后端澄清业务行为；这里展示 GET 清单与命令选项；公共认证、bridge 和错误映射仍待评审，不代表接口已发布。精确 HTTP、JSON 位于折叠区。</p>'
        '<div class="review-guide-steps">'
        '<div class="review-guide-step"><strong>1. 先看触发场景</strong><span>确认用户什么时候会调用这个接口。</span></div>'
        '<div class="review-guide-step"><strong>2. 再看界面结果</strong><span>确认前端如何展示成功、不可用和失败。</span></div>'
        '<div class="review-guide-step"><strong>3. 最后核对报文</strong><span>研发按需展开原始字段、Header 和响应。</span></div>'
        '</div></section>'
    )


def render_business_flow(flow: list[dict[str, str]]) -> str:
    steps = []
    for index, item in enumerate(flow, start=1):
        steps.append(
            '<div class="business-step">'
            f'<strong>{index}. {html.escape(item["actor"])}</strong>'
            f'<span>{html.escape(item["action"])}</span>'
            f'<span class="muted">{html.escape(item["outcome"])}</span>'
            '</div>'
        )
    return '<div class="business-flow">' + ''.join(steps) + '</div>'


INPUT_LABELS = {"text": "文本输入", "options": "调用命令选项接口"}


def command_state(command: dict[str, Any]) -> list[str]:
    hint = "、".join(command.get("hints", [])) or "无提示"
    files = "允许附件" if command["type"] == "skill" else "无附件"
    input_type = INPUT_LABELS.get(command.get("inputType"), "无参数，直接执行")
    return [f'/{command["name"]}', command["description"], input_type, hint, files]


def render_command_example(operation: dict[str, Any]) -> str:
    sections = []
    for response in operation["responses"]:
        if response["status"] != "200":
            continue
        commands = response["bodies"]["zh-CN"]["result"]["commands"]
        rows = [command_state(command) for command in commands]
        sections.append(
            '<section class="business-section">'
            f'<h3>{html.escape(response["tabLabel"])}</h3>'
            f'<p>{html.escape(response["summary"])}</p>'
            f'{SHARED.static_table(["命令", "用途", "输入方式", "输入提示", "附件"], rows)}</section>'
        )
    return ''.join(sections)


def render_options_example(operation: dict[str, Any]) -> str:
    sections = []
    for response in operation["responses"]:
        if response["status"] != "200":
            continue
        result = response["bodies"]["zh-CN"]["result"]
        rows = [[option["value"], option["label"], "当前值" if option["value"] == result["current"] else ""]
                for option in result["options"]] or [["（无候选）", "", f'当前值 {result["current"]}']]
        sections.append(
            '<section class="business-section">'
            f'<h3>{html.escape(response["tabLabel"])}</h3>'
            f'<p>{html.escape(response["summary"])}</p>'
            f'{SHARED.static_table(["value（提交）", "label（展示）", "状态"], rows)}</section>'
        )
    return ''.join(sections)


def response_code(response: dict[str, Any]) -> str | None:
    codes = []
    for payload in response.get("bodies", {}).values():
        if isinstance(payload, dict) and payload.get("resCode"):
            codes.append(str(payload["resCode"]))
    unique = list(dict.fromkeys(codes))
    return " / ".join(unique) if unique else None


def render_error_summary(operation: dict[str, Any]) -> str:
    rows = []
    for response in operation["responses"]:
        code = response_code(response)
        if code is not None and code != "0":
            rows.append([response["status"], code, response["summary"]])
    if not rows:
        return ""
    return (
        '<section class="business-section"><h3>失败时前端需要区分什么</h3>'
        f'{SHARED.static_table(["HTTP", "错误码", "发生场景"], rows)}</section>'
    )


def render_business_review(model: dict[str, Any]) -> str:
    operation = model["operation"]
    view = model["review"]["businessView"]
    sections = [
        '<article class="business-surface" data-business-review>',
        '<header class="business-head"><span class="business-badge">业务评审视图</span>',
        f'<h2>{html.escape(operation["shortName"])}</h2>',
        f'<p class="business-summary">{html.escape(view["summary"])}</p></header>',
        '<section class="business-section"><h3>前后端怎么交互</h3>',
        render_business_flow(view["flow"]),
        '</section>',
    ]
    if operation["operationKey"] == "ListChatCommands":
        sections.append(render_command_example(operation))
    elif operation["operationKey"] == "ListChatCommandOptions":
        sections.append(render_options_example(operation))
    sections.append(render_error_summary(operation))
    for note in view.get("notes", []):
        sections.append(
            '<section class="business-section">'
            f'<p class="business-note">{html.escape(note)}</p></section>'
        )
    sections.append('</article>')
    return ''.join(sections)


def load_contract() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    common = json.loads((CONTRACT_ROOT / "common.json").read_text(encoding="utf-8"))
    SHARED.require(isinstance(common, dict), "common.json must contain a JSON object")
    operation_paths = sorted((CONTRACT_ROOT / "操作").glob("*.json"))
    SHARED.require(operation_paths, "No public command operation models found")
    sources = [json.loads(path.read_text(encoding="utf-8")) for path in operation_paths]
    SHARED.require(all(isinstance(source, dict) for source in sources), "Operation sources must be JSON objects")
    models = [SHARED.expand_model(common, source) for source in sources]
    keys = [model["operation"]["operationKey"] for model in models]
    identities = [f'{model["operation"]["method"]} {model["operation"]["path"]}' for model in models]
    SHARED.require(len(keys) == len(set(keys)), "operationKey values must be unique")
    SHARED.require(len(identities) == len(set(identities)), "HTTP operation identities must be unique")
    return common, models


def build_html() -> str:
    _, models = load_contract()
    shared_css = (RUNTIME_ROOT / "接口契约" / "页面资源" / "review.css").read_text(encoding="utf-8").strip()
    css = f"{shared_css}\n{BUSINESS_CSS.strip()}"
    script = (RUNTIME_ROOT / "接口契约" / "页面资源" / "review.js").read_text(encoding="utf-8").strip()
    cards = []
    for index, model in enumerate(models):
        operation_key = model["operation"]["operationKey"]
        cards.append(
            f'<section class="company-api-review" data-operation-review="{html.escape(operation_key, quote=True)}" '
            f'data-operation-index="{index}">{render_business_review(model)}'
            '<details class="exact-contract"><summary>查看 GET HTTP / JSON 报文（公共边界待评审）</summary>'
            '<div class="api-shell" data-api-shell aria-live="polite">'
            f'{SHARED.render_static(model)}</div></details></section>'
        )
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="referrer" content="no-referrer">
  <title>{html.escape(models[0]["api"]["title"])} - API Review</title>
  <style>
{css}
  </style>
</head>
<body>
  <!-- Generated from 接口契约/common.json and 接口契约/操作/*.json. Do not edit this HTML directly. -->
  <main>
{render_page_guide()}
{"".join(cards)}
  </main>
  <script type="application/json" id="api-review-models">{SHARED.encode_models(models)}</script>
  <script>
{script}
  </script>
</body>
</html>
'''


def write_output(destination: Path, content: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=destination.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, destination)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    content = build_html()
    destination = args.output.resolve()
    if args.check:
        SHARED.require(destination.exists(), f"Generated HTML is missing: {destination}")
        SHARED.require(destination.read_text(encoding="utf-8") == content, "Generated HTML is out of date")
    else:
        write_output(destination, content)
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

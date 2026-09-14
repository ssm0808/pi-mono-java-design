#!/usr/bin/env python3
"""Shared contract rendering helpers; use render_chat_api.py to publish Runtime HTML."""

from __future__ import annotations

import copy
import html
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
CONTRACT_ROOT = ROOT / "接口契约"
COMMON_PATH = CONTRACT_ROOT / "common.json"
OPERATIONS_ROOT = CONTRACT_ROOT / "操作"
CSS_PATH = CONTRACT_ROOT / "页面资源" / "review.css"
JS_PATH = CONTRACT_ROOT / "页面资源" / "review.js"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path.relative_to(ROOT)} must contain a JSON object")
    return value


def deep_merge(base: Any, override: Any) -> Any:
    if not isinstance(base, dict) or not isinstance(override, dict):
        return copy.deepcopy(override)
    result = copy.deepcopy(base)
    for key, value in override.items():
        result[key] = deep_merge(result[key], value) if key in result else copy.deepcopy(value)
    return result


def lookup(common: dict[str, Any], reference: str) -> Any:
    value: Any = common
    for part in reference.split("."):
        require(isinstance(value, dict) and part in value, f"Unknown common reference: {reference}")
        value = value[part]
    return copy.deepcopy(value)


def resolve_entry(common: dict[str, Any], entry: Any) -> Any:
    if not isinstance(entry, dict) or "$ref" not in entry:
        return resolve_value(common, entry)
    reference = entry["$ref"]
    require(isinstance(reference, str), "$ref must be a string")
    override = {key: value for key, value in entry.items() if key != "$ref"}
    resolved = lookup(common, reference)
    if not isinstance(resolved, dict):
        require(not override, f"Primitive common reference cannot be overridden: {reference}")
        return resolve_value(common, resolved)
    return resolve_value(common, deep_merge(resolved, override))


def resolve_value(common: dict[str, Any], value: Any) -> Any:
    if isinstance(value, dict):
        if "$ref" in value:
            return resolve_entry(common, value)
        return {key: resolve_value(common, item) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve_value(common, item) for item in value]
    return copy.deepcopy(value)


def expand_model(common: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    operation = copy.deepcopy(source.get("operation"))
    require(isinstance(operation, dict), "operation source must contain an operation object")
    operation.setdefault("requestHeaderExamples", copy.deepcopy(common["requestHeaderExamples"]))
    operation["parameters"] = [resolve_entry(common, item) for item in operation.get("parameters", [])]
    operation["responses"] = [resolve_entry(common, item) for item in operation.get("responses", [])]
    operation["contractSections"] = [resolve_entry(common, item) for item in operation.get("contractSections", [])]
    model = {
        "api": copy.deepcopy(common["api"]),
        "operation": operation,
        "review": copy.deepcopy(source.get("review", {"questions": []})),
    }
    validate_model(model)
    return model


def validate_model(model: dict[str, Any]) -> None:
    api = model["api"]
    operation = model["operation"]
    for key in ("title", "version", "basePath", "visibility", "fieldNaming", "headerNaming"):
        require(isinstance(api.get(key), str) and api[key], f"api.{key} is required")
    for key in ("shortName", "operationKey", "method", "path", "summary", "description"):
        require(isinstance(operation.get(key), str) and operation[key], f"operation.{key} is required")
    require(operation["method"] in {"GET", "POST", "PUT", "DELETE"}, "Unsupported HTTP method")
    require(
        isinstance(operation.get("requestHeaderExamples"), list) and operation["requestHeaderExamples"],
        "requestHeaderExamples are required",
    )
    require(isinstance(operation.get("parameters"), list), "parameters must be an array")
    require(isinstance(operation.get("requestBody"), dict), "requestBody must be an object")
    require(isinstance(operation.get("responses"), list) and operation["responses"], "responses are required")


def load_contract() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    common = read_json(COMMON_PATH)
    operation_paths = sorted(OPERATIONS_ROOT.glob("*.json"))
    require(operation_paths, "No operation contract models found")
    models = [expand_model(common, read_json(path)) for path in operation_paths]
    keys = [model["operation"]["operationKey"] for model in models]
    identities = [f'{model["operation"]["method"]} {model["operation"]["path"]}' for model in models]
    require(len(keys) == len(set(keys)), "operationKey values must be unique")
    require(len(identities) == len(set(identities)), "HTTP operation identities must be unique")
    return common, models


def static_pre(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
    return f"<pre><code>{html.escape(text)}</code></pre>"


def static_table(columns: list[str], rows: list[list[Any]]) -> str:
    head = "".join(f"<th>{html.escape(column)}</th>" for column in columns)
    body = []
    for row in rows:
        cells = "".join(
            f'<td data-label="{html.escape(columns[index], quote=True)}">{html.escape(str(value))}</td>'
            for index, value in enumerate(row)
        )
        body.append(f"<tr>{cells}</tr>")
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def static_response(response: dict[str, Any], index: int, *, expand_details: bool = False) -> str:
    tab_label = response.get("tabLabel") or response["status"]
    summary = f'{response["status"]} {response["label"]} — {response["summary"]}'
    locales = []
    for locale_index, (locale, payload) in enumerate(response["bodies"].items()):
        headers = dict(response.get("headers", {}))
        if locale != "default" and "Content-Language" in headers:
            headers["Content-Language"] = locale
        header_lines = [f"{name}: {value}" for name, value in headers.items()]
        rendered = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, indent=2)
        output = "\n".join([*header_lines, "" if header_lines else "", rendered]).lstrip("\n")
        open_attribute = " open" if expand_details or locale_index == 0 else ""
        locales.append(
            f'<details class="static-choice"{open_attribute}><summary>{html.escape(locale)}</summary>{static_pre(output)}</details>'
        )
    open_attribute = " open" if expand_details or index == 0 else ""
    return (
        f'<details class="static-response"{open_attribute}>'
        f'<summary><code>{html.escape(str(tab_label))}</code> {html.escape(summary)}</summary>'
        f'{"".join(locales)}</details>'
    )


def static_review(model: dict[str, Any]) -> str:
    review = model.get("review", {})
    questions = review.get("questions", [])
    if not questions:
        return ""
    operation_key = model["operation"]["operationKey"]
    fields = []
    for question in questions:
        options = []
        for option in question["options"]:
            checked = " checked" if option.get("selected") else ""
            options.append(
                '<label class="review-option">'
                f'<input type="radio" name="{html.escape(operation_key)}-{html.escape(question["id"])}" '
                f'value="{html.escape(option["value"], quote=True)}"{checked}>'
                f'<span><strong>{html.escape(option["label"])}</strong>'
                f'<small>{html.escape(option.get("description", ""))}</small></span></label>'
            )
        fields.append(
            f'<fieldset data-question-id="{html.escape(question["id"], quote=True)}">'
            f'<legend>{html.escape(question["legend"])}</legend>{"".join(options)}</fieldset>'
        )
    notice = review.get("notice", "选择后可直接发送本轮评审答复。")
    return (
        '<section class="section review-section"><div class="review-heading">'
        '<div><h3>本轮需要你确认</h3>'
        f'<p class="muted">{html.escape(notice)}</p></div>'
        f'<span class="review-status">{html.escape(review.get("status", "评审中"))}</span></div>'
        f'<form class="review-form" data-review-form data-operation-key="{html.escape(operation_key, quote=True)}">'
        f'{"".join(fields)}<label class="review-notes">补充说明（可选）'
        '<textarea name="notes" rows="3" placeholder="例如：只调整第 2 项，其余采用推荐项。"></textarea></label>'
        '<div class="review-actions"><button type="submit" class="review-submit">发送评审答复</button>'
        '<span class="review-feedback" data-review-feedback aria-live="polite"></span></div></form></section>'
    )


def render_static(model: dict[str, Any], *, expand_details: bool = False) -> str:
    api = model["api"]
    operation = model["operation"]
    full_path = f'{api["basePath"].rstrip("/")}/{operation["path"].lstrip("/")}'
    method = operation["method"].lower()
    auth_blocks = []
    for auth_index, mode in enumerate(operation["requestHeaderExamples"]):
        rows = [
            [item["name"], "是" if item["required"] else "否", item["value"], item["description"]]
            for item in mode["headers"]
        ]
        request = "\n".join(
            [f'{operation["method"]} {full_path}', *(f'{item["name"]}: {item["value"]}' for item in mode["headers"])]
        )
        open_attribute = " open" if expand_details or mode.get("preferred") or auth_index == 0 else ""
        auth_blocks.append(
            f'<details class="static-choice"{open_attribute}><summary>{html.escape(mode["label"])}</summary>'
            f'{static_table(["Header", "必填", "示例值", "说明"], rows)}{static_pre(request)}</details>'
        )
    parameters = operation["parameters"]
    parameter_html = static_table(
        ["位置", "名称", "必填", "约束", "说明"],
        [
            [item["in"], item["name"], "是" if item["required"] else "否", item.get("schema", "—"), item["description"]]
            for item in parameters
        ],
    ) if parameters else '<p class="muted empty">无 path/query/header 业务参数。</p>'
    request_body = operation["requestBody"]
    request_example = static_pre(request_body["example"]) if request_body.get("example") is not None else ""
    request_examples = []
    for example_index, example in enumerate(request_body.get("examples", [])):
        open_attribute = " open" if expand_details or example_index == 0 else ""
        request_examples.append(
            f'<details class="static-choice"{open_attribute}><summary>{html.escape(example["label"])}</summary>'
            f'<p class="muted empty">{html.escape(example.get("description", ""))}</p>'
            f'{static_pre(example["value"])}</details>'
        )
    responses = "".join(static_response(response, index, expand_details=expand_details)
                        for index, response in enumerate(operation["responses"]))
    sections = "".join(
        f'<section class="section contract-detail"><h3>{html.escape(item["title"])}</h3>'
        f'<p class="description">{html.escape(item.get("description", ""))}</p>'
        f'{static_table(item["columns"], item["rows"])}</section>'
        for item in operation.get("contractSections", [])
    )
    return (
        '<div data-static-review>'
        '<header class="topbar"><div class="row">'
        f'<h2>{html.escape(api["title"])}</h2><span class="tag">{html.escape(api["version"])}</span>'
        f'<span class="tag">{html.escape(api["visibility"])}</span>'
        f'<span class="tag">字段：{html.escape(api["fieldNaming"])}</span>'
        f'<span class="tag">Header：{html.escape(api["headerNaming"])}</span></div>'
        f'<code class="base">{html.escape(api["basePath"])}</code></header>'
        f'<article class="operation operation-{method}">'
        '<header class="operation-head">'
        f'<span class="method method-{method}">{html.escape(operation["method"])}</span>'
        f'<code class="path">{html.escape(operation["path"])}</code>'
        f'<span class="muted">{html.escape(operation["summary"])}</span>'
        f'<span class="operation-name">{html.escape(operation["shortName"])}</span>'
        f'<code class="operation-key">{html.escape(operation["operationKey"])}</code></header>'
        f'{static_review(model) if model.get("review", {}).get("batchReview") else ""}'
        f'<section class="section"><h3>作用</h3><p class="description">{html.escape(operation["description"])}</p></section>'
        f'<section class="section contract-detail auth-section"><h3>调用上下文 Header</h3>{"".join(auth_blocks)}</section>'
        '<section class="section contract-detail request-section"><h3>参数与请求体</h3>'
        f'{parameter_html}<p class="muted empty">{html.escape(request_body.get("description", "无请求体。"))}</p>'
        f'{request_example}{"".join(request_examples)}</section>{sections}'
        f'<section class="section contract-detail response-section"><h3>响应</h3>{responses}</section>'
        f'{static_review(model) if not model.get("review", {}).get("batchReview") else ""}</article></div>'
    )


def encode_models(models: list[dict[str, Any]]) -> str:
    encoded = json.dumps(models, ensure_ascii=False, separators=(",", ":"))
    return encoded.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def build_operation_html(models: list[dict[str, Any]]) -> str:
    """Render supplied review models using the shared Runtime presentation."""
    css = CSS_PATH.read_text(encoding="utf-8").strip()
    script = JS_PATH.read_text(encoding="utf-8").strip()
    cards = []
    for index, model in enumerate(models):
        operation_key = model["operation"]["operationKey"]
        cards.append(
            f'<section class="company-api-review" data-operation-review="{html.escape(operation_key, quote=True)}" '
            f'data-operation-index="{index}"><div class="api-shell" data-api-shell aria-live="polite">'
            f'{render_static(model)}</div></section>'
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
  <!-- Generated from operation review models. Do not edit this HTML directly. -->
  <main>
{"".join(cards)}
  </main>
  <script type="application/json" id="api-review-models">{encode_models(models)}</script>
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

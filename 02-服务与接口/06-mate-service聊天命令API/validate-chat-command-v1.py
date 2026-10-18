#!/usr/bin/env python3
"""Validate the source-first mate-service Chat Command contract and artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from render_chat_command_v1 import build_html, load_contract, RUNTIME_ROOT

sys.path.insert(0, str(RUNTIME_ROOT))
from command_catalog_contract import (ARGUMENT_TYPE_BY_COMMAND,
                                      validate_catalog_examples, validate_projection_pair)


ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = ROOT.parents[1]
HTML_PATH = ROOT / "chat-command-v1-review.html"
DESIGN_PATH = ROOT / "README.md"
LOWER_CAMEL = re.compile(r"^[a-z][A-Za-z0-9]*$")
EXPECTED_OPERATIONS = {
    ("GET", "/chats/{chatId}/commands"),
    ("GET", "/chats/{chatId}/commands/{commandName}/options"),
}
OPERATION_KEYS = {"ListChatCommands", "ListChatCommandOptions"}
OPTION_COMMAND_NAMES = [name for name, argument_type in ARGUMENT_TYPE_BY_COMMAND.items() if argument_type == "options"]
# Each Mate thinking/mode example mirrors the Runtime Session query example it is built from.
RUNTIME_VALUE_SOURCES = {
    "200-thinking": ("09-list-session-thinking-values.json", "200-thinking-values"),
    "200-thinking-unsupported": ("09-list-session-thinking-values.json", "200-thinking-unsupported"),
    "200-mode": ("10-list-session-modes.json", "200-modes"),
}


class ReviewHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.static_count = 0
        self.business_count = 0
        self.exact_contract_count = 0
        self.open_exact_contract_count = 0
        self.styles: list[str] = []
        self.scripts: list[tuple[dict[str, str | None], str]] = []
        self.visible: list[str] = []
        self.capture: str | None = None
        self.attributes: dict[str, str | None] = {}
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if "data-static-review" in attributes:
            self.static_count += 1
        if "data-business-review" in attributes:
            self.business_count += 1
        if tag == "details" and "exact-contract" in (attributes.get("class") or "").split():
            self.exact_contract_count += 1
            if "open" in attributes:
                self.open_exact_contract_count += 1
        if tag in {"style", "script"}:
            self.capture = tag
            self.attributes = attributes
            self.parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag != self.capture:
            return
        source = "".join(self.parts)
        if tag == "style":
            self.styles.append(source)
        else:
            self.scripts.append((self.attributes, source))
        self.capture = None
        self.attributes = {}
        self.parts = []

    def handle_data(self, data: str) -> None:
        if self.capture is not None:
            self.parts.append(data)
        elif data.strip():
            self.visible.append(data.strip())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run(command: list[str], cwd: Path = ROOT) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def validate_keys(value: Any, context: str) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            require(LOWER_CAMEL.fullmatch(key) is not None, f"Non-lowerCamel field in {context}: {key}")
            validate_keys(nested, context)
    elif isinstance(value, list):
        for item in value:
            validate_keys(item, context)


def values_for_key(value: Any, key: str):
    if isinstance(value, dict):
        for current, nested in value.items():
            if current == key:
                yield nested
            yield from values_for_key(nested, key)
    elif isinstance(value, list):
        for item in value:
            yield from values_for_key(item, key)


def validate_contract(common: dict[str, Any], models: list[dict[str, Any]]) -> None:
    require(common["api"]["version"] == "1.8.0", "Unexpected public contract version")
    require(common["api"]["basePath"] == "/mate-service/v1", "Unexpected public base path")
    require("GET 字段已确认" in common["api"]["visibility"] and "公共边界待评审" in common["api"]["visibility"],
            "GET confirmation must not approve the public boundary")
    require("commandLimits" not in common and "commandNamePatterns" not in common,
            "Retired POST-only common definitions must not return")
    headers = {
        header["name"]
        for example in common["requestHeaderExamples"]
        for header in example["headers"]
    }
    require(headers == {"Authorization"}, "Public auth must not expose internal Header names")
    operations = {(model["operation"]["method"], model["operation"]["path"]) for model in models}
    require(operations == EXPECTED_OPERATIONS, "Public operation inventory differs")
    require(len(models) == 2, "Expected the public GET catalog and command options")
    require({model["operation"]["operationKey"] for model in models} == OPERATION_KEYS,
            "Operation keys must use PascalCase")
    for model in models:
        operation = model["operation"]
        business_view = model["review"].get("businessView")
        require(isinstance(business_view, dict), "Human review business view is required")
        require(isinstance(business_view.get("summary"), str) and business_view["summary"],
                "Human review summary is required")
        require(isinstance(business_view.get("flow"), list) and business_view["flow"],
                "Human review flow is required")
        require("待评审、待实现" in business_view["summary"] and "不得作为已发布接口的依据" in business_view["summary"],
                "Operation must state the pending 待实现 public boundary")
        require(not re.search(r"已确认|已评审|待实现|待评审", operation["description"]),
                "Purpose must describe behavior rather than review status")
        placeholders = re.findall(r"{([^}]+)}", operation["path"])
        require(all(LOWER_CAMEL.fullmatch(item) for item in placeholders), "Path fields must be lowerCamelCase")
        for response in operation["responses"]:
            for body in response.get("bodies", {}).values():
                if isinstance(body, (dict, list)):
                    validate_keys(body, operation["operationKey"])
    validate_catalog(models)
    validate_command_options(models)


def validate_catalog(models: list[dict[str, Any]]) -> None:
    operation = operation_by_key(models, "ListChatCommands")
    validate_catalog_examples(operation)
    runtime = json.loads((RUNTIME_ROOT / "接口契约/操作/12-list-agent-commands.json").read_text(encoding="utf-8"))
    validate_projection_pair(runtime["operation"], operation)
    codes = set(values_for_key(operation["responses"], "resCode"))
    require({"UNAUTHENTICATED", "CHAT_ACCESS_DENIED", "CHAT_NOT_FOUND", "COMMAND_CATALOG_UNAVAILABLE"} <= codes,
            "Catalog public errors are incomplete")


def validate_command_options(models: list[dict[str, Any]]) -> None:
    operation = operation_by_key(models, "ListChatCommandOptions")
    command_name = next(item for item in operation["parameters"] if item["name"] == "commandName")
    require(command_name["in"] == "path" and command_name["schema"] == " | ".join(OPTION_COMMAND_NAMES),
            "commandName must list exactly the commands whose argumentType is options")
    examples = {response["id"]: response for response in operation["responses"] if response["status"] == "200"}
    require(set(examples) == {"200-model", "200-model-empty"} | set(RUNTIME_VALUE_SOURCES),
            "Options require model, thinking (supported and unsupported), mode and empty-model examples")
    session_models = runtime_session_models()
    for example_id, response in examples.items():
        chinese, english = localized_option_results(response)
        submit_values = [option["value"] for option in chinese["options"]]
        if example_id == "200-model":
            require(submit_values == session_models["models"]
                    and chinese["currentValue"] == session_models["currentModelId"],
                    "Model options must come from the Session model list")
            require(chinese["options"] == english["options"],
                    "Model names are business data and do not follow Accept-Language")
        elif example_id == "200-model-empty":
            require(submit_values == [] and chinese["currentValue"] == session_models["currentModelId"],
                    "Empty model options keep the current model")
        else:
            runtime = runtime_session_values(*RUNTIME_VALUE_SOURCES[example_id])
            require(submit_values == runtime["values"] and chinese["currentValue"] == runtime["currentValue"],
                    f"{example_id} must mirror the Runtime Session values, current value included")
            require(all(zh["label"] != en["label"] for zh, en in zip(chinese["options"], english["options"])),
                    f"{example_id} labels follow Accept-Language")
    codes = set(values_for_key(operation["responses"], "resCode"))
    require({"INVALID_CHAT_ID", "UNAUTHENTICATED", "CHAT_ACCESS_DENIED", "CHAT_NOT_FOUND",
             "COMMAND_OPTIONS_NOT_FOUND", "COMMAND_OPTIONS_UNAVAILABLE"} <= codes,
            "Options public errors are incomplete")


def operation_by_key(models: list[dict[str, Any]], operation_key: str) -> dict[str, Any]:
    return next(model["operation"] for model in models if model["operation"]["operationKey"] == operation_key)


def runtime_session_models() -> dict[str, Any]:
    source = json.loads((RUNTIME_ROOT / "接口契约/操作/06-list-session-models.json").read_text(encoding="utf-8"))
    return next(iter(source["operation"]["responses"][0]["bodies"].values()))["result"]


def runtime_session_values(source_name: str, example_id: str) -> dict[str, Any]:
    source = json.loads((RUNTIME_ROOT / "接口契约/操作" / source_name).read_text(encoding="utf-8"))
    response = next(item for item in source["operation"]["responses"] if item.get("id") == example_id)
    return next(iter(response["bodies"].values()))["result"]


def localized_option_results(response: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Check one success example and return its zh-CN and en-US results."""
    require(response["headers"].get("Cache-Control") == "no-store", "Options must not be cached")
    require(set(response["bodies"]) == {"zh-CN", "en-US"}, "Options examples must cover zh-CN and en-US")
    for body in response["bodies"].values():
        require(set(body) == {"resCode", "resMsg", "result"} and body["resCode"] == "0", "Options ResultBean differs")
        validate_option_result(body["result"])
    chinese, english = response["bodies"]["zh-CN"]["result"], response["bodies"]["en-US"]["result"]
    require(chinese["currentValue"] == english["currentValue"]
            and [option["value"] for option in chinese["options"]] == [option["value"] for option in english["options"]],
            "Submit values and the current value are language-neutral")
    return chinese, english


def validate_option_result(result: dict[str, Any]) -> None:
    require(set(result) == {"currentValue", "options"} and nonblank(result["currentValue"]),
            "Options carry the current value and the candidates only")
    for option in result["options"]:
        require(set(option) == {"value", "label"} and nonblank(option["value"]) and nonblank(option["label"]),
                "Each option has a submit value and a display label")


def nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_html(models: list[dict[str, Any]]) -> None:
    source = HTML_PATH.read_text(encoding="utf-8")
    require(source == build_html(), "Generated public review HTML is stale")
    parser = ReviewHtmlParser()
    parser.feed(source)
    require(parser.static_count == 2, "No-script operation count is wrong")
    require(parser.business_count == 2, "Business review operation count is wrong")
    require(parser.exact_contract_count == 2, "Exact contract fold count is wrong")
    require(parser.open_exact_contract_count == 0, "Raw protocol must be folded by default")
    require(len(parser.styles) == 1, "Expected one shared style block")
    model_scripts = [json.loads(script) for attrs, script in parser.scripts
                     if attrs.get("type") == "application/json" and attrs.get("id") == "api-review-models"]
    require(model_scripts == [models], "Embedded review models differ from sources")
    executable = [script for attrs, script in parser.scripts if attrs.get("type") != "application/json"]
    require(len(executable) == 1, "Expected one executable script")
    with tempfile.TemporaryDirectory() as directory:
        script_path = Path(directory) / "review.js"
        script_path.write_text(executable[0], encoding="utf-8")
        run(["node", "--check", str(script_path)])
    visible = " ".join(parser.visible)
    for heading in ("业务评审视图", "前后端怎么交互", "作用", "调用上下文 Header", "参数与请求体", "响应"):
        require(heading in visible, f"No-script review is missing {heading}")
    require("查看 GET HTTP / JSON 报文（公共边界待评审）" in visible,
            "Raw protocol fold is missing")
    require(source.index("data-business-review") < source.index("class=\"exact-contract\""),
            "Business review must appear before the raw protocol")
    require("字段：lowerCamelCase" in visible and "Header：保留原名" in visible,
            "Review does not expose naming rules")
    require(re.search(r"@media\s*\(max-width:\s*680px\)", source) is not None,
            "Mobile breakpoint is missing")
    require("content: attr(data-label)" in source, "Responsive labeled rows are missing")


def validate_retirement(root: Path = ROOT) -> None:
    retired = (
        "接口契约/操作/02-execute-chat-command.json",
        "设计图/diagram.puml",
        "设计图/public_command_boundary.svg",
        "设计图/public_sse_projection.svg",
    )
    for path in retired:
        require(not (root / path).exists(), f"Retired Command artifact returned: {path}")
    sources = {path.name for path in (root / "接口契约/操作").glob("*.json")}
    require(sources == {"01-list-chat-commands.json", "02-list-chat-command-options.json"},
            "Only the GET catalog and options models may remain")


def validate_markdown() -> None:
    content = DESIGN_PATH.read_text(encoding="utf-8")
    require("```mermaid" not in content, "Mermaid is forbidden")
    require("目录" not in content, "Public Command design must use 命令清单 or an explicit file term")
    for target in re.findall(r"!\[[^\]]*\]\(([^)]+\.svg)\)", content):
        require((ROOT / target).exists(), f"Missing SVG link: {target}")
    for target, line_text in re.findall(r"\[[^\]]+\]\(([^)#]+\.puml)#L([0-9]+)\)", content):
        source = (ROOT / target).resolve()
        lines = source.read_text(encoding="ascii").splitlines()
        line = int(line_text)
        require(0 < line <= len(lines) and lines[line - 1].startswith("@startuml"),
                f"Invalid PlantUML source anchor: {target}#L{line}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="reserved for parity with other contract validators")
    parser.parse_args()
    common, models = load_contract()
    validate_contract(common, models)
    require("目录" not in json.dumps(models, ensure_ascii=False),
            "Public Command contract must use 命令清单 or an explicit file term")
    validate_html(models)
    validate_retirement()
    validate_markdown()
    run(["git", "diff", "--check"], REPOSITORY_ROOT)
    print("mate-service Chat Command contract validation passed: GET projection and command options; public boundary pending; retired POST and diagrams absent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

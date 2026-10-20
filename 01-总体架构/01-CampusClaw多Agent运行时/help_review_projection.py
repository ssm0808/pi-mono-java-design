"""Derive the Help view from the authoritative Runtime operation; no second JSON source."""

from copy import deepcopy

from render_chat_http_v1 import load_contract, require


HELP_ERROR_IDS = {
    "400-invalid-session-id", "400-invalid-command-request",
    "404-session-not-found", "422-agent-not-available",
}


def project_help_model(runtime_model):
    model = deepcopy(runtime_model)
    operation = model["operation"]
    require(operation["operationKey"] == "ExecuteSessionCommand", "Help needs the Command operation")
    headers = [mode for mode in operation["requestHeaderExamples"] if mode["id"] == "builtin"]
    require(len(headers) == 1, "Expected exactly one canonical Builtin Header example")
    operation["requestHeaderExamples"] = headers
    examples = [example for example in operation["requestBody"].get("examples", [])
                if example.get("value") == {"name": "help"}]
    require(len(examples) == 1, "Expected exactly one canonical Help request example")
    successes = [response for response in operation["responses"]
                 if response.get("id", "").startswith("200-help")]
    errors = [response for response in operation["responses"] if response.get("id") in HELP_ERROR_IDS]
    require({response["id"] for response in successes} == {"200-help", "200-help-empty"},
            "Canonical Help successes are incomplete")
    require({response["id"] for response in errors} == HELP_ERROR_IDS, "Canonical Help errors are incomplete")
    model["api"]["title"] = "Help：Agent 使用指南（已确认）"
    model["api"]["visibility"] = "Internal · Help 已确认；Runtime Command 的只读专项展示"
    operation["shortName"] = "Help：Agent 使用指南"
    operation["summary"] = "查询 Agent 使用指南"
    operation["description"] = ("返回当前会话绑定 Agent 的使用指南：一段按请求语言生成的 Markdown 文本，"
                                "包含 Agent 名称、用途说明和使用场景，供用户了解如何使用该 Agent。")
    operation["requestBody"]["example"] = deepcopy(examples[0]["value"])
    operation["requestBody"]["examples"] = examples
    operation["responses"] = successes + errors
    model["review"] = {"questions": []}
    return model


def load_help_model():
    _, models = load_contract()
    runtime = next(model for model in models
                   if model["operation"]["operationKey"] == "ExecuteSessionCommand")
    return project_help_model(runtime)

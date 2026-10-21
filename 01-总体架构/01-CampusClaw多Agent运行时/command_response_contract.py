"""Cross-operation design checks; these do not execute the Java implementation."""

from command_catalog_contract import ARGUMENT_TYPE_BY_COMMAND, BUILTINS, require
from request_header_contract import validate_no_client_tokens


# Every Builtin success returns only readable Markdown text; the caller then GETs the Session for state.
BUILTIN_TEXT_CASES = (
    "200-help", "200-help-empty", "200-status",
    "200-rename", "200-rename-unchanged",
    "200-model", "200-model-unchanged",
    "200-thinking", "200-thinking-unchanged",
    "200-mode-plan", "200-mode-build", "200-mode-unchanged",
    "200-compact", "200-compact-empty",
    "200-skills", "200-skills-populated",
)
# Each changing command documents its same-value outcome as its own text.
UNCHANGED_PAIRS = (("200-rename", "200-rename-unchanged"), ("200-model", "200-model-unchanged"),
                   ("200-thinking", "200-thinking-unchanged"), ("200-mode-build", "200-mode-unchanged"))
RETIRED_CASES = {"200-name", "200-name-updated", "200-name-unchanged", "200-model-query", "200-model-query-empty",
                 "200-thinking-query", "200-mode-query"}
RETIRED_FIELDS = {"command", "changed", "sourceEventSeq", "commandId", "entryId", "entrySeq", "eventId",
                  "resourceVersion", "revision", "etag"}
EXECUTE_ERROR_CODES = {
    ("400", "INVALID_SESSION_ID"), ("400", "INVALID_COMMAND_REQUEST"),
    ("404", "SESSION_NOT_FOUND"), ("404", "COMMAND_NOT_FOUND"),
    ("409", "SESSION_BUSY"),
    ("422", "AGENT_NOT_AVAILABLE"), ("422", "SKILL_NOT_AVAILABLE"), ("422", "MODEL_NOT_AVAILABLE"),
    ("422", "THINKING_NOT_SUPPORTED"), ("422", "PLAN_MODE_UNAVAILABLE"),
    ("500", "SESSION_NAME_UPDATE_FAILED"), ("500", "SESSION_UPDATE_FAILED"),
    ("500", "EVENT_ACCEPTANCE_FAILED"), ("500", "COMMAND_EXECUTION_FAILED"),
    ("503", "EVENT_SERVICE_UNAVAILABLE"), ("503", "RUNTIME_CAPACITY_EXCEEDED"), ("503", "MANAGER_UNAVAILABLE"),
}
# Skill Commands share the user-message acceptance chain, so their failures use its precise codes.
RETIRED_EXECUTE_ERROR_CODES = {("503", "SKILL_AGENT_UNAVAILABLE"), ("500", "SKILL_PREPARATION_FAILED")}


def same_shape(value, baseline, path="result", nullable_name=False):
    """Compare exact recursive fields/types, allowing the existing nullable Session name."""
    if nullable_name and path == "result.displayName":
        require(value is None or isinstance(value, str), "Session displayName must be string or null")
        return
    if isinstance(baseline, dict):
        require(isinstance(value, dict) and set(value) == set(baseline), f"Fields differ at {path}")
        require(not (set(value) & RETIRED_FIELDS), f"Internal receipt leaked at {path}")
        for field, expected in baseline.items():
            same_shape(value[field], expected, f"{path}.{field}", nullable_name)
    elif isinstance(baseline, list):
        require(isinstance(value, list), f"Expected array at {path}")
        require(bool(baseline), f"Missing baseline item shape at {path}")
        for item in value:
            same_shape(item, baseline[0], f"{path}[]")
    elif type(baseline) in (int, float):
        require(type(value) in (int, float), f"Expected number at {path}")
    else:
        require(type(value) is type(baseline), f"Type differs at {path}")


def success(operation):
    response = next(item for item in operation["responses"] if item["status"] == "200")
    return next(iter(response["bodies"].values()))["result"]


def validate_text_result(result, identity):
    require(not (set(result) & RETIRED_FIELDS), f"Internal receipt leaked at {identity}")
    require(set(result) == {"text"}, f"Builtin result must contain only text: {identity}")
    text = result["text"]
    require(isinstance(text, str) and bool(text.strip()) and text == text.strip(),
            f"Builtin text must be a non-empty, trimmed Markdown string: {identity}")


def builtin_cases(operation):
    responses = [item for item in operation["responses"] if item["status"] == "200" and item["id"] != "200-skill-message"]
    cases = {item["id"]: item for item in responses}
    require(len(cases) == len(responses) and set(cases) == set(BUILTIN_TEXT_CASES),
            "Builtin text response cases differ (changed, unchanged and empty outcomes)")
    require(not (set(cases) & RETIRED_CASES), "Retired no-argument query or /name examples returned")
    return cases


def validate_response_reuse(models):
    operations = {model["operation"]["operationKey"]: model["operation"] for model in models}
    for operation in operations.values():
        validate_no_client_tokens(operation)
    command = operations["ExecuteSessionCommand"]
    validate_request_examples(command)
    validate_mode_examples(command)
    validate_error_codes(command)
    session = success(operations["GetSession"])
    require(session.get("mode") in {"plan", "build"}, "Session response must include mode")
    for response in operations["UpdateSession"]["responses"]:
        if response["status"] == "200":
            for body in response["bodies"].values():
                same_shape(body["result"], session, nullable_name=True)
                require(body["result"]["mode"] in {"plan", "build"}, "Invalid Session mode")
    for response in operations["CreateSession"]["responses"]:
        if response["status"] == "201":
            for body in response["bodies"].values():
                require(body["result"].get("mode") == "build", "Created Session must default to build")
    cases = builtin_cases(command)
    for identity, response in cases.items():
        headers = response["headers"]
        require(set(headers) == {"Content-Type", "Cache-Control", "Content-Language"},
                f"Response headers differ: {identity}")
        require(headers["Content-Type"] == "application/json" and headers["Cache-Control"] == "no-store",
                f"Command must return noncached ordinary JSON: {identity}")
        require("zh-CN" in response["bodies"], f"Missing zh-CN text example: {identity}")
        for locale, body in response["bodies"].items():
            require(headers["Content-Language"] == locale, f"Response locale differs: {identity}")
            require(set(body) == {"resCode", "resMsg", "result"} and body["resCode"] == "0"
                    and body["resMsg"] == "success", f"ResultBean differs: {identity}")
            validate_text_result(body["result"], identity)
    validate_scenarios(cases)


def validate_scenarios(cases):
    text = lambda identity: cases[identity]["bodies"]["zh-CN"]["result"]["text"]
    texts = [text(identity) for identity in BUILTIN_TEXT_CASES]
    require(len(set(texts)) == len(texts), "Each Builtin outcome needs its own text; examples must not collapse")
    for changed, unchanged in UNCHANGED_PAIRS:
        require("未修改" in text(unchanged) and "未修改" not in text(changed),
                f"Same-value text must say nothing changed: {unchanged}")
    require(text("200-mode-plan") != text("200-mode-build"), "Mode switch examples must keep their target mode")
    require("\n- " in text("200-skills-populated") and "\n- " not in text("200-skills"),
            "Missing empty/populated skills cases")


def validate_request_examples(operation):
    examples = [item["value"] for item in operation["requestBody"]["examples"]]
    builtins = [example for example in examples if example.get("name") in BUILTINS]
    require([example["name"] for example in builtins if example["name"] != "mode"]
            == [name for name in BUILTINS if name != "mode"],
            "Each Builtin needs one request example, in catalog order")
    for example in builtins:
        require(set(example) <= {"name", "arguments"}, f"Builtin request accepts only name and arguments: {example}")
        if example["name"] in ARGUMENT_TYPE_BY_COMMAND:
            arguments = example.get("arguments")
            require(isinstance(arguments, str) and bool(arguments.strip()),
                    f"Argument is required; no no-argument query example: {example['name']}")
        else:
            require("arguments" not in example, f"Builtin takes no argument: {example['name']}")


def validate_mode_examples(operation):
    examples = [item["value"] for item in operation["requestBody"]["examples"]
                if item["value"].get("name") == "mode"]
    require(examples == [{"name": "mode", "arguments": "plan"}, {"name": "mode", "arguments": "build"}],
            "Mode must cover both switches without a query or new fields")
    require(any(response["status"] == "422" and
                response.get("bodies", {}).get("zh-CN", {}).get("resCode") == "PLAN_MODE_UNAVAILABLE"
                for response in operation["responses"]), "Mode requires a plan-capability error example")


def validate_error_codes(operation):
    codes = {(response["status"], body.get("resCode")) for response in operation["responses"]
             if response["status"] != "200" for body in response.get("bodies", {}).values()}
    require(not (codes & RETIRED_EXECUTE_ERROR_CODES), "Retired Skill error codes returned")
    require(codes == EXECUTE_ERROR_CODES, f"POST Command error codes differ: {sorted(codes ^ EXECUTE_ERROR_CODES)}")

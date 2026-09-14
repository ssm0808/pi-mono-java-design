"""Cross-operation design checks; these do not execute the Java implementation."""

import re

from command_catalog_contract import require


SESSION_CASES = {
    "200-status", "200-name", "200-name-updated", "200-name-unchanged",
    "200-model", "200-model-unchanged", "200-thinking-query",
    "200-thinking", "200-thinking-unchanged",
}
MODEL_CASES = {"200-model-query", "200-model-query-empty"}
BUSINESS_SHAPES = {
    "200-help": {"displayName": "Agent", "description": ["text"], "userCases": ["text"]},
    "200-help-empty": {"displayName": "Agent", "description": ["text"], "userCases": ["text"]},
    "200-compact": {"compacted": True},
    "200-compact-empty": {"compacted": False},
    "200-skills": {"skills": [{"name": "pdf", "description": "text"}]},
    "200-skills-populated": {"skills": [{"name": "pdf", "description": "text"}]},
}
RETIRED_FIELDS = {"command", "changed", "sourceEventSeq", "commandId", "entryId", "entrySeq", "eventId"}


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


def validate_response_reuse(models):
    operations = {model["operation"]["operationKey"]: model["operation"] for model in models}
    session = success(operations["getSession"])
    model_list = success(operations["listSessionModels"])
    require(session.get("mode") in {"plan", "build"}, "Session response must include mode")
    for response in operations["updateSession"]["responses"]:
        if response["status"] == "200":
            for body in response["bodies"].values():
                same_shape(body["result"], session, nullable_name=True)
                require(body["result"]["mode"] in {"plan", "build"}, "Invalid Session mode")
    for response in operations["createSession"]["responses"]:
        if response["status"] == "201":
            for body in response["bodies"].values():
                require(body["result"].get("mode") == "build", "Created Session must default to build")
    responses = [item for item in operations["executeSessionCommand"]["responses"] if item["status"] == "200" and item["id"] != "200-skill-message"]
    cases = {item["id"]: item for item in responses}
    require(len(cases) == len(responses) and set(cases) == SESSION_CASES | MODEL_CASES | set(BUSINESS_SHAPES),
            "Command query, mutation, unchanged and empty response cases differ")
    for identity, response in cases.items():
        expected = session if identity in SESSION_CASES else (
            model_list if identity in MODEL_CASES else BUSINESS_SHAPES[identity])
        headers = response["headers"]
        required = {"Content-Type", "Cache-Control", "Content-Language"}
        require(set(headers) == required | ({"ETag"} if identity in SESSION_CASES else set()),
                f"Response headers differ: {identity}")
        require(headers["Content-Type"] == "application/json" and headers["Cache-Control"] == "no-store",
                f"Command must return noncached ordinary JSON: {identity}")
        if identity in SESSION_CASES:
            require(isinstance(headers["ETag"], str) and re.fullmatch(r'"snp-[A-Za-z0-9_-]+"', headers["ETag"]),
                    f"Session ETag must use the existing opaque format: {identity}")
        require(bool(response["bodies"]), f"Missing response bodies: {identity}")
        for locale, body in response["bodies"].items():
            require(headers["Content-Language"] == locale, f"Response locale differs: {identity}")
            require(set(body) == {"resCode", "resMsg", "result"} and body["resCode"] == "0"
                    and body["resMsg"] == "success", f"ResultBean differs: {identity}")
            same_shape(body["result"], expected, nullable_name=identity in SESSION_CASES)
    validate_scenarios(cases)


def validate_scenarios(cases):
    result = lambda identity: cases[identity]["bodies"]["zh-CN"]["result"]
    require(result("200-name")["displayName"] is None, "Missing nullable Session name example")
    for identity in ("200-status", "200-thinking-query", "200-name-updated"):
        require(result(identity)["state"] == "running", f"Missing running query/name example: {identity}")
    for identity in ("200-model", "200-thinking"):
        require(result(identity)["state"] == "idle", f"Mutation example must be idle: {identity}")
    require(result("200-model")["thinking"] is False, "Missing model normalization example")
    require(result("200-thinking")["thinking"] is True, "Thinking on example differs")
    for changed in ("200-name-updated", "200-model", "200-thinking"):
        unchanged = "200-name-unchanged" if changed == "200-name-updated" else changed + "-unchanged"
        require(result(changed) == result(unchanged), f"Same-value resource differs: {unchanged}")
        require(cases[changed]["headers"]["ETag"] == cases[unchanged]["headers"]["ETag"],
                f"Same-value ETag differs: {unchanged}")
    require(result("200-model-query-empty")["models"] == [] and
            result("200-model-query-empty")["currentModelId"] == result("200-model-query")["currentModelId"],
            "Empty models must retain the current model outside candidates")
    require(bool(result("200-model-query")["models"]), "Missing populated model list")
    require(result("200-compact")["compacted"] is True and
            result("200-compact-empty")["compacted"] is False, "Missing compact true/false cases")
    require(result("200-skills")["skills"] == [] and bool(result("200-skills-populated")["skills"]),
            "Missing empty/populated skills cases")
    for identity in ("200-skills", "200-skills-populated"):
        names = [item["name"] for item in result(identity)["skills"]]
        require(names == sorted(set(names)), "Skills must be unique and name-sorted")

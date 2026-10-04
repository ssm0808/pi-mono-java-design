"""Validate operation-specific request headers across the ten-operation catalog."""

CREDENTIALS = {"X-HW-ID", "Authorization", "X-HW-APPKEY", "access-token"}
EXECUTION = {"SubmitSessionEvent", "ExecuteSessionCommand"}
JSON_BODY = EXECUTION | {"UpdateSession", "QuerySkillLoadStatistics"}
JSON_MODE = {"UpdateSession", "QuerySkillLoadStatistics", "ListSessionEvents"}
RETIRED_HEADERS = {"if-match", "idempotency-key", "etag"}
RETIRED_INPUTS = {"ifMatch", "etag", "expectedVersion", "resourceVersion", "revision",
                  "version", "clientVersion", "idempotencyKey", "requestKey", "requestId"}
RETIRED_ERRORS = {"IF_MATCH_REQUIRED", "SESSION_VERSION_MISMATCH"}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def validate_request_headers(operation):
    validate_no_client_tokens(operation)
    key = operation["operationKey"]
    examples = operation["requestHeaderExamples"]
    expected_modes = ({"jwt", "appkey", "control"} if key == "SubmitSessionEvent" else
                      {"jwt", "appkey", "builtin"} if key == "ExecuteSessionCommand" else
                      {"json"} if key in JSON_MODE else {"language"})
    require(len(examples) == len(expected_modes)
            and {mode["id"] for mode in examples} == expected_modes,
            f"{key}: Header modes differ; ordinary operations retain only the language/JSON mode")
    require(sum(mode.get("preferred") is True for mode in examples) == 1,
            f"{key}: exactly one preferred Header mode is required")
    for mode in examples:
        validate_mode(key, mode)
    parameters = {p["name"]: p for p in operation["parameters"] if p["in"] == "header"}
    require(set(parameters) == {"Accept-Language"},
            f"{key}: parameters must retain only language")
    require(parameters["Accept-Language"]["required"] is False,
            f"{key}: language must remain optional")
    require(operation["requestBody"]["contentType"] == ("application/json" if key in JSON_BODY else None),
            f"{key}: request body content type differs")
    policy = operation.get("credentialPolicy", {})
    if key == "SubmitSessionEvent":
        require(policy.get("captureEventTypes") == ["user.message"]
                and policy.get("controlEventsReuseOriginalCredentials") is True,
                "Only user.message captures credentials; control events reuse original credentials")
    if key == "ExecuteSessionCommand":
        require(policy.get("callerCredentialScope") == "skill"
                and policy.get("builtinRequiresCredentials") is False,
                "Builtin callers must not require execution credentials")


def validate_no_client_tokens(operation):
    """Reject retired contract declarations; this does not reject extra inbound headers."""
    key = operation["operationKey"]
    for parameter in operation["parameters"]:
        require(not (parameter["in"] == "header" and parameter["name"].lower() in RETIRED_HEADERS),
                f"{key}: retired client token Header must not return")
        require(not (parameter["in"] == "query" and parameter["name"] in RETIRED_INPUTS),
                f"{key}: query must not replace retired client tokens")
    for mode in operation.get("requestHeaderExamples", []):
        require(not any(header["name"].lower() in RETIRED_HEADERS for header in mode["headers"]),
                f"{key}: retired client token Header example must not return")
    for response in operation["responses"]:
        require(not any(name.lower() in RETIRED_HEADERS for name in response.get("headers", {})),
                f"{key}: retired client token response Header must not return")
        require(response["status"] not in {"412", "428"},
                f"{key}: retired client precondition status must not return")
        for body in response.get("bodies", {}).values():
            if isinstance(body, dict):
                require(body.get("resCode") not in RETIRED_ERRORS,
                        f"{key}: retired client precondition error must not return")
    request = operation["requestBody"]
    require(not (set(request.get("schema", {}).get("properties", {})) & RETIRED_INPUTS),
            f"{key}: body must not replace retired client tokens")
    examples = [request.get("example"), *(item["value"] for item in request.get("examples", []))]
    require(not any(isinstance(example, dict) and set(example) & RETIRED_INPUTS for example in examples),
            f"{key}: body example must not replace retired client tokens")


def validate_mode(key, mode):
    headers = {h["name"]: h for h in mode["headers"]}
    require(len(headers) == len(mode["headers"]), f"{key}: duplicate Header")
    expected = {"Accept-Language": ("zh-CN", False)}
    if key in JSON_BODY:
        expected["Content-Type"] = ("application/json", True)
    if key in JSON_MODE or key in EXECUTION:
        sse = key == "SubmitSessionEvent" or (key == "ExecuteSessionCommand" and mode["id"] != "builtin")
        expected["Accept"] = ("text/event-stream" if sse else "application/json", key == "SubmitSessionEvent")
    if key in EXECUTION and mode["id"] in {"jwt", "appkey"}:
        jwt = mode["id"] == "jwt"
        expected.update({"X-HW-ID": ("credential-jwt" if jwt else "credential-appkey", False),
                         "Authorization" if jwt else "X-HW-APPKEY":
                             ("Bearer opaque-token" if jwt else "opaque-appkey", False),
                         "access-token": ("opaque-access-token", False)})
    actual = {name: (h.get("value"), h.get("required")) for name, h in headers.items()}
    require(actual == expected,
            f"{key}/{mode['id']}: Header values/requiredness differ; nonexecution must remain without credentials")
    for name, header in headers.items():
        require(bool(header.get("description")), f"{key}: Header description missing: {name}")
        if name in CREDENTIALS:
            description = header["description"]
            for phrase in ("内存", "Mate tool execute"):
                require(phrase in description, f"{key}: credential lifetime/forwarding rule missing")
            if key == "ExecuteSessionCommand":
                require("不写入 Session、事件或日志" in description,
                        f"{key}: credential persistence prohibition missing")
        for forbidden in ("公司调用方标识", "瞬态", "瞬时", "<CALLER_ID>", "<JWT>", "<APPKEY>", "<ACCESS_TOKEN>"):
            require(forbidden not in str(header), f"{key}: obsolete Header wording: {forbidden}")
    if "X-HW-APPKEY" in headers:
        require("可与 Authorization 同时" in headers["X-HW-APPKEY"]["description"],
                f"{key}: simultaneous credentials must remain supported")
    if "X-HW-ID" in headers:
        require("用户凭据 ID" in headers["X-HW-ID"]["description"]
                and "不是公司、服务或应用标识" in headers["X-HW-ID"]["description"],
                f"{key}: X-HW-ID is a user credential ID")

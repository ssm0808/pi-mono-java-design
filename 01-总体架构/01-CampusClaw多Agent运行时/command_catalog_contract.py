"""Shared design checks for the lightweight Runtime command descriptors and option values."""

import re

BUILTINS = ("help", "status", "rename", "model", "thinking", "mode", "compact", "skills")
# Builtins returned when the catalog request omits sessionId: commands that affect a new Session or explain the
# Agent. status and compact only read or change an existing Session, so they stay in the full catalog only.
AGENT_BUILTINS = ("help", "rename", "model", "thinking", "mode", "skills")
DESCRIPTOR_FIELDS = {"name", "type", "description", "argumentType", "argumentRequired"}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def validate_descriptor(command):
    require(isinstance(command, dict), "Descriptor must be an object")
    require({"name", "type", "description"} <= set(command) <= DESCRIPTOR_FIELDS,
            "Descriptor fields differ from lightweight contract")
    require(all(isinstance(command[key], str) and command[key].strip()
                for key in ("name", "type", "description")), "Required descriptor strings must be nonblank")
    require(command["type"] in {"builtin", "skill"}, "Unexpected command type")
    if command["type"] == "builtin":
        require(command["name"] in BUILTINS, "Unexpected Builtin")
    else:
        require(re.fullmatch(r"skill:[a-z0-9]+(?:-[a-z0-9]+)*", command["name"])
                and len(command["name"]) <= 70, "Invalid Skill command name")
    require(command.get("argumentType") == expected_argument_type(command),
            f"argumentType must follow the command's argument: {command['name']}")
    require(("argumentRequired" in command) == ("argumentType" in command),
            f"argumentRequired is present exactly when argumentType is: {command['name']}")
    if "argumentRequired" in command:
        require(command["argumentRequired"] is expected_argument_required(command),
                f"argumentRequired must follow the command's argument: {command['name']}")


def validate_commands(commands, scope="session"):
    require(isinstance(commands, list), "Commands must be a non-null list")
    for command in commands:
        validate_descriptor(command)
    names = [command["name"] for command in commands]
    require(len(names) == len(set(names)), "Duplicate command")
    skills = [command for command in commands if command["type"] == "skill"]
    builtins = BUILTINS if scope == "session" else AGENT_BUILTINS
    require(names == list(builtins) + sorted(command["name"] for command in skills),
            f"{scope} catalog must list its Builtins in fixed order, then Skills by name, without state filtering")
    for command in commands:
        if command["name"] == "help":
            require(command["description"] in HELP_DESCRIPTIONS.values(), "Help must remain Agent guide")


HELP_DESCRIPTIONS = {"zh-CN": "介绍当前智能体的用途和使用场景", "en-US": "Introduce this agent's purpose and use cases"}
# How each command takes its argument, so any client picks the input control without per-command logic.
# text: free text; options: values from ListAgentCommandValues. Skills take text; Builtins not listed take none.
ARGUMENT_TYPE_BY_COMMAND = {"rename": "text", "model": "options", "thinking": "options", "mode": "options"}


def expected_argument_type(command):
    return "text" if command.get("type") == "skill" else ARGUMENT_TYPE_BY_COMMAND.get(command.get("name"))


def expected_argument_required(command):
    """Builtins with an argument only change state, so the argument is required; Skill text stays optional."""
    return command.get("type") != "skill"


SESSION_SUCCESS_IDS = {"200-commands", "200-no-skills"}
AGENT_SUCCESS_ID = "200-agent-commands"
CATALOG_ERROR_CODES = {("400", "INVALID_AGENT_ID"), ("400", "INVALID_SESSION_ID"), ("404", "AGENT_NOT_FOUND"),
                       ("404", "SESSION_NOT_FOUND"), ("422", "AGENT_NOT_AVAILABLE"),
                       ("503", "AGENT_SERVICE_UNAVAILABLE")}


def accepts_optional_session(operation):
    return any(parameter.get("in") == "query" and parameter.get("name") == "sessionId"
               and parameter.get("required") is False for parameter in operation["parameters"])


def error_codes(operation):
    return {(response["status"], body.get("resCode")) for response in operation["responses"]
            if response["status"] != "200" for body in response.get("bodies", {}).values()}


def success_examples(operation):
    require(accepts_optional_session(operation), "Agent command catalog must take sessionId as an optional query")
    expected = SESSION_SUCCESS_IDS | {AGENT_SUCCESS_ID}
    successes = [response for response in operation["responses"] if response["status"] == "200"]
    require(len(successes) == len(expected) and {response.get("id") for response in successes} == expected,
            "Catalog requires the populated, no-Skill and no-Session examples exactly once")
    return {response["id"]: response for response in successes}


def validate_catalog_examples(operation):
    examples = success_examples(operation)
    for response in examples.values():
        require(response["headers"].get("Cache-Control") == "no-store", "GET must not cache the catalog")
        require(set(response["bodies"]) == set(HELP_DESCRIPTIONS), "Catalog examples must cover zh-CN and en-US")
        for language, body in response["bodies"].items():
            require(set(body) == {"resCode", "resMsg", "result"} and body["resCode"] == "0"
                    and body["resMsg"] == "success" and set(body["result"]) == {"commands"},
                    "Catalog ResultBean differs")
            validate_commands(body["result"]["commands"], scope_of(response))
            help_command = next(command for command in body["result"]["commands"] if command["name"] == "help")
            require(help_command["description"] == HELP_DESCRIPTIONS[language],
                    f"Builtin description must follow Accept-Language: {language}")
        validate_localized_pair(*(response["bodies"][language]["result"]["commands"] for language in ("zh-CN", "en-US")))
    full = examples["200-commands"]["bodies"]["zh-CN"]["result"]["commands"]
    empty = examples["200-no-skills"]["bodies"]["zh-CN"]["result"]["commands"]
    require(any(command["type"] == "skill" for command in full), "Populated example must include a Skill")
    require(empty == [command for command in full if command["type"] == "builtin"],
            "No-Skill example must keep identical Builtin descriptors")
    for language in HELP_DESCRIPTIONS:
        session = examples["200-commands"]["bodies"][language]["result"]["commands"]
        agent = examples[AGENT_SUCCESS_ID]["bodies"][language]["result"]["commands"]
        require(agent == [command for command in session
                          if command["type"] == "skill" or command["name"] in AGENT_BUILTINS],
                "No-Session catalog must be the Session catalog without status and compact")
    require(error_codes(operation) == CATALOG_ERROR_CODES, "Agent command catalog error codes differ")
    require("ListAgentCommandValues" in operation["description"],
            "Catalog must leave option values to ListAgentCommandValues")


def scope_of(response):
    return "agent" if response.get("id") == AGENT_SUCCESS_ID else "session"


def validate_localized_pair(chinese, english):
    require(len(chinese) == len(english), "Localized catalogs must list the same commands")
    for left, right in zip(chinese, english):
        require((left["name"], left["type"]) == (right["name"], right["type"]),
                "name and type stay language-neutral")
        for field in ("argumentType", "argumentRequired"):
            require(left.get(field) == right.get(field) and (field in left) == (field in right),
                    f"{field} is language-neutral: {left['name']}")
        if left["type"] == "builtin":
            require(left["description"] != right["description"], f"Builtin description is not localized: {left['name']}")
        else:
            require(left["description"] == right["description"], f"Skill description must be returned as authored: {left['name']}")


OPTION_COMMANDS = tuple(name for name, argument_type in ARGUMENT_TYPE_BY_COMMAND.items() if argument_type == "options")
# With sessionId: one example per option command and value state. Without sessionId (-agent): the initial values a
# Session created now would use.
SESSION_VALUE_IDS = ("200-model", "200-model-empty", "200-thinking", "200-thinking-unsupported", "200-mode")
AGENT_VALUE_IDS = ("200-model-agent", "200-thinking-agent", "200-mode-agent")
VALUE_EXAMPLE_IDS = SESSION_VALUE_IDS + AGENT_VALUE_IDS
VALUE_ERROR_CODES = {("400", "INVALID_AGENT_ID"), ("400", "INVALID_SESSION_ID"), ("404", "SESSION_NOT_FOUND"),
                     ("404", "AGENT_NOT_FOUND"), ("404", "COMMAND_VALUES_NOT_FOUND"),
                     ("422", "AGENT_NOT_AVAILABLE"), ("503", "AGENT_SERVICE_UNAVAILABLE"),
                     ("503", "MANAGER_UNAVAILABLE")}


def value_examples(operation):
    """Return {example id: {currentValue, values}} for the ListAgentCommandValues success examples."""
    successes = [response for response in operation["responses"] if response["status"] == "200"]
    require([response.get("id") for response in successes] == list(VALUE_EXAMPLE_IDS),
            "Command values require model, empty model, thinking (supported and unsupported), mode "
            "and the three no-Session examples")
    results = {}
    for response in successes:
        require(response["headers"].get("Cache-Control") == "no-store", "Command values must not be cached")
        bodies = list(response["bodies"].values())
        require(len(bodies) == 1 and set(bodies[0]) == {"resCode", "resMsg", "result"} and bodies[0]["resCode"] == "0",
                "Command values ResultBean differs")
        result = bodies[0]["result"]
        require(set(result) == {"currentValue", "values"} and isinstance(result["currentValue"], str)
                and isinstance(result["values"], list), "Command values carry the current value and the values only")
        session_scoped = response["id"] in SESSION_VALUE_IDS
        require(response.get("summary", "").startswith("带 sessionId" if session_scoped else "不带 sessionId"),
                f"Command values example must state its sessionId scope: {response['id']}")
        results[response["id"]] = result
    return results


def validate_command_values(operation, created_session):
    """One Agent-scoped query serves every option command; without sessionId it returns a new Session's values."""
    require(operation["path"] == "/agents/{agentId}/commands/{commandName}/values",
            "Command values are queried per Agent, like the command catalog")
    require(accepts_optional_session(operation), "Command values must take sessionId as an optional query")
    command_name = next(item for item in operation["parameters"] if item.get("name") == "commandName")
    require(command_name["in"] == "path" and command_name["schema"] == " | ".join(OPTION_COMMANDS),
            "commandName must list exactly the commands whose argumentType is options")
    results = value_examples(operation)
    require(bool(results["200-model"]["values"]) and results["200-model"]["currentValue"] in results["200-model"]["values"],
            "Model values list the selectable models, including the current one")
    require(results["200-model-empty"] == {"currentValue": results["200-model"]["currentValue"], "values": []},
            "Empty model values keep the current model")
    require(results["200-thinking"] == {"currentValue": "on", "values": ["on", "off"]}
            and results["200-thinking-unsupported"] == {"currentValue": "off", "values": ["off"]},
            "Thinking values are on/off, or off only when the model does not support thinking")
    require(results["200-mode"]["values"] == ["plan", "build"]
            and results["200-mode"]["currentValue"] in results["200-mode"]["values"], "Mode values are plan and build")
    require(results["200-model-agent"] == {"currentValue": created_session["modelId"],
                                           "values": results["200-model"]["values"]},
            "No-Session model values use the created Session's default model and the same selectable models")
    require(results["200-thinking-agent"] == {"currentValue": "on" if created_session["thinking"] else "off",
                                              "values": ["on", "off"]},
            "No-Session thinking follows the default model, which must support thinking")
    require(results["200-mode-agent"] == {"currentValue": created_session["mode"], "values": ["plan", "build"]},
            "No-Session mode starts from the Agent's published mode")
    require(error_codes(operation) == VALUE_ERROR_CODES, "Command values error codes differ")

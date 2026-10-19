"""Shared design checks for lightweight Runtime and Mate GET descriptors."""

import re

BUILTINS = ("help", "status", "name", "model", "thinking", "mode", "compact", "skills")
# Builtins that need no Session; returned when the catalog request omits sessionId.
AGENT_BUILTINS = ("help", "skills")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def validate_descriptor(command):
    require(isinstance(command, dict), "Descriptor must be an object")
    require({"name", "type", "description"} <= set(command)
            and set(command) <= {"name", "type", "description", "argumentType"},
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
# text: free text; options: values from ListSessionCommandValues, shown through Mate command options.
# Skills take text; Builtins not listed take no argument.
ARGUMENT_TYPE_BY_COMMAND = {"name": "text", "model": "options", "thinking": "options", "mode": "options"}


def expected_argument_type(command):
    return "text" if command.get("type") == "skill" else ARGUMENT_TYPE_BY_COMMAND.get(command.get("name"))


SESSION_SUCCESS_IDS = {"200-commands", "200-no-skills"}
AGENT_SUCCESS_ID = "200-agent-commands"


def accepts_optional_session(operation):
    return any(parameter.get("in") == "query" and parameter.get("name") == "sessionId"
               and parameter.get("required") is False for parameter in operation["parameters"])


def success_examples(operation):
    expected = SESSION_SUCCESS_IDS | ({AGENT_SUCCESS_ID} if accepts_optional_session(operation) else set())
    successes = [response for response in operation["responses"] if response["status"] == "200"]
    require(len(successes) == len(expected) and {response.get("id") for response in successes} == expected,
            "Catalog requires the populated, no-Skill and (with optional sessionId) no-Session examples exactly once")
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
    if AGENT_SUCCESS_ID in examples:
        for language in HELP_DESCRIPTIONS:
            session = examples["200-commands"]["bodies"][language]["result"]["commands"]
            agent = examples[AGENT_SUCCESS_ID]["bodies"][language]["result"]["commands"]
            require(agent == [command for command in session
                              if command["type"] == "skill" or command["name"] in AGENT_BUILTINS],
                    "No-Session catalog must be the Session catalog without Session Builtins")


def scope_of(response):
    return "agent" if response.get("id") == AGENT_SUCCESS_ID else "session"


def validate_localized_pair(chinese, english):
    require(len(chinese) == len(english), "Localized catalogs must list the same commands")
    for left, right in zip(chinese, english):
        require((left["name"], left["type"]) == (right["name"], right["type"]),
                "name and type stay language-neutral")
        require(left.get("argumentType") == right.get("argumentType"),
                f"argumentType is language-neutral: {left['name']}")
        if left["type"] == "builtin":
            require(left["description"] != right["description"], f"Builtin description is not localized: {left['name']}")
        else:
            require(left["description"] == right["description"], f"Skill description must be returned as authored: {left['name']}")


def validate_projection_pair(runtime, public):
    validate_catalog_examples(runtime)
    validate_catalog_examples(public)
    left, right = success_examples(runtime), success_examples(public)
    require(set(right) == SESSION_SUCCESS_IDS, "Mate maps every Chat to a Session and projects only the full catalog")
    for identity in right:
        require(left[identity]["bodies"] == right[identity]["bodies"], "Mate GET projection drifted from Runtime")


OPTION_COMMANDS = tuple(name for name, argument_type in ARGUMENT_TYPE_BY_COMMAND.items() if argument_type == "options")
# One example per option command and value state; Mate options examples reuse these ids.
VALUE_EXAMPLE_IDS = ("200-model", "200-model-empty", "200-thinking", "200-thinking-unsupported", "200-mode")


def value_examples(operation):
    """Return {example id: {currentValue, values}} for the ListSessionCommandValues success examples."""
    successes = [response for response in operation["responses"] if response["status"] == "200"]
    require([response.get("id") for response in successes] == list(VALUE_EXAMPLE_IDS),
            "Command values require model, empty model, thinking (supported and unsupported) and mode examples")
    results = {}
    for response in successes:
        require(response["headers"].get("Cache-Control") == "no-store", "Command values must not be cached")
        bodies = list(response["bodies"].values())
        require(len(bodies) == 1 and set(bodies[0]) == {"resCode", "resMsg", "result"} and bodies[0]["resCode"] == "0",
                "Command values ResultBean differs")
        result = bodies[0]["result"]
        require(set(result) == {"currentValue", "values"} and isinstance(result["currentValue"], str)
                and isinstance(result["values"], list), "Command values carry the current value and the values only")
        results[response["id"]] = result
    return results


def validate_command_values(operation, model_query):
    """One query serves every option command; model matches the /model query result, thinking follows the model."""
    command_name = next(item for item in operation["parameters"] if item.get("name") == "commandName")
    require(command_name["in"] == "path" and command_name["schema"] == " | ".join(OPTION_COMMANDS),
            "commandName must list exactly the commands whose argumentType is options")
    results = value_examples(operation)
    require(results["200-model"] == {"currentValue": model_query["currentModelId"], "values": model_query["models"]},
            "Model values must be the models the /model query returns")
    require(results["200-model-empty"] == {"currentValue": model_query["currentModelId"], "values": []},
            "Empty model values keep the current model")
    require(results["200-thinking"] == {"currentValue": "on", "values": ["on", "off"]}
            and results["200-thinking-unsupported"] == {"currentValue": "off", "values": ["off"]},
            "Thinking values are on/off, or off only when the model does not support thinking")
    require(results["200-mode"]["values"] == ["plan", "build"]
            and results["200-mode"]["currentValue"] in results["200-mode"]["values"], "Mode values are plan and build")
    codes = {(response["status"], body.get("resCode")) for response in operation["responses"]
             for body in response.get("bodies", {}).values()}
    require(("404", "COMMAND_VALUES_NOT_FOUND") in codes, "Commands without values must return 404")

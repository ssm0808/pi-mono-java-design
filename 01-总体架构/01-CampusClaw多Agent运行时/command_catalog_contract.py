"""Shared design checks for lightweight Runtime and Mate GET descriptors."""

import copy
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
            and set(command) <= {"name", "type", "description", "argumentHint"},
            "Descriptor fields differ from lightweight contract")
    require(all(isinstance(command[key], str) and command[key].strip()
                for key in ("name", "type", "description")), "Required descriptor strings must be nonblank")
    require(command["type"] in {"builtin", "skill"}, "Unexpected command type")
    if command["type"] == "builtin":
        require(command["name"] in BUILTINS, "Unexpected Builtin")
    else:
        require(re.fullmatch(r"skill:[a-z0-9]+(?:-[a-z0-9]+)*", command["name"])
                and len(command["name"]) <= 70, "Invalid Skill command name")
    expected = BUILTIN_ARGUMENT_HINTS.get(command["name"])
    if expected is None:
        require("argumentHint" not in command, f"Only Builtins with an argument return argumentHint: {command['name']}")
    else:
        require(command.get("argumentHint") == expected,
                f"argumentHint must be the placeholder for the argument, not its values: {command['name']}")


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
# Placeholder per Builtin that takes an argument, as pi's argumentHint; Skills omit it.
# Values to choose from come from the Session (ListSessionModels, ListSessionThinkingValues, ListSessionModes).
BUILTIN_ARGUMENT_HINTS = {"name": "<name>", "model": "<model>", "thinking": "<level>", "mode": "<mode>"}


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
        require(left.get("argumentHint") == right.get("argumentHint"),
                f"argumentHint is language-neutral: {left['name']}")
        if left["type"] == "builtin":
            require(left["description"] != right["description"], f"Builtin description is not localized: {left['name']}")
        else:
            require(left["description"] == right["description"], f"Skill description must be returned as authored: {left['name']}")


# Mate adds argumentType so any frontend picks the input control without per-command logic.
# Skill commands always take text; Builtins not listed take no argument.
ARGUMENT_TYPE_BY_COMMAND = {"name": "text", "model": "options", "thinking": "options", "mode": "options"}


def expected_argument_type(command):
    return "text" if command.get("type") == "skill" else ARGUMENT_TYPE_BY_COMMAND.get(command.get("name"))


def to_runtime_projection(public_operation):
    """Check the Mate-only argumentType, then return the operation as Runtime projects it."""
    projection = copy.deepcopy(public_operation)
    for response in projection["responses"]:
        if response["status"] != "200":
            continue
        for body in response["bodies"].values():
            for command in body["result"]["commands"]:
                argument_type = command.pop("argumentType", None)
                require(argument_type == expected_argument_type(command),
                        f"Public argumentType must follow the Mate mapping: {command.get('name')}")
    return projection


def validate_projection_pair(runtime, public):
    public = to_runtime_projection(public)
    validate_catalog_examples(runtime)
    validate_catalog_examples(public)
    left, right = success_examples(runtime), success_examples(public)
    require(set(right) == SESSION_SUCCESS_IDS, "Mate maps every Chat to a Session and projects only the full catalog")
    for identity in right:
        require(left[identity]["bodies"] == right[identity]["bodies"], "Mate GET projection drifted from Runtime")

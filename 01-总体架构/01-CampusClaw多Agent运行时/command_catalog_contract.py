"""Shared design checks for lightweight Runtime and Mate GET descriptors."""

import re

BUILTINS = ("help", "status", "name", "model", "thinking", "mode", "compact", "skills")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def validate_descriptor(command):
    require(isinstance(command, dict), "Descriptor must be an object")
    require({"name", "type", "description"} <= set(command)
            and set(command) <= {"name", "type", "description", "hints"},
            "Descriptor fields differ from lightweight contract")
    require(all(isinstance(command[key], str) and command[key].strip()
                for key in ("name", "type", "description")), "Required descriptor strings must be nonblank")
    require(command["type"] in {"builtin", "skill"}, "Unexpected command type")
    if command["type"] == "builtin":
        require(command["name"] in BUILTINS, "Unexpected Builtin")
    else:
        require(re.fullmatch(r"skill:[a-z0-9]+(?:-[a-z0-9]+)*", command["name"])
                and len(command["name"]) <= 70, "Invalid Skill command name")
    if "hints" in command:
        require(isinstance(command["hints"], list)
                and all(isinstance(hint, str) and hint.strip() for hint in command["hints"]),
                "Hints must be an array of nonblank strings, independent of input capability")


def validate_commands(commands):
    require(isinstance(commands, list), "Commands must be a non-null list")
    for command in commands:
        validate_descriptor(command)
    names = [command["name"] for command in commands]
    require(len(names) == len(set(names)), "Duplicate command")
    skills = [command for command in commands if command["type"] == "skill"]
    require(names == list(BUILTINS) + sorted(command["name"] for command in skills),
            "Agent catalog must list every Builtin in fixed order, then Skills by name, without state filtering")
    for command in commands:
        if command["name"] == "help":
            require(command["description"] in HELP_DESCRIPTIONS.values(), "Help must remain Agent guide")


HELP_DESCRIPTIONS = {"zh-CN": "介绍当前 Agent 的用途和使用场景", "en-US": "Introduce this Agent's purpose and use cases"}


SUCCESS_IDS = {"200-commands", "200-no-skills"}


def success_examples(operation):
    successes = [response for response in operation["responses"] if response["status"] == "200"]
    require(len(successes) == 2 and {response.get("id") for response in successes} == SUCCESS_IDS,
            "Agent catalog requires the populated and no-Skill examples exactly once")
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
            validate_commands(body["result"]["commands"])
            help_command = next(command for command in body["result"]["commands"] if command["name"] == "help")
            require(help_command["description"] == HELP_DESCRIPTIONS[language],
                    f"Builtin description must follow Accept-Language: {language}")
        validate_localized_pair(*(response["bodies"][language]["result"]["commands"] for language in ("zh-CN", "en-US")))
    full = examples["200-commands"]["bodies"]["zh-CN"]["result"]["commands"]
    empty = examples["200-no-skills"]["bodies"]["zh-CN"]["result"]["commands"]
    require(any(command["type"] == "skill" for command in full), "Populated example must include a Skill")
    require(empty == [command for command in full if command["type"] == "builtin"],
            "No-Skill example must keep identical Builtin descriptors")


def validate_localized_pair(chinese, english):
    require(len(chinese) == len(english), "Localized catalogs must list the same commands")
    for left, right in zip(chinese, english):
        require((left["name"], left["type"], left.get("hints")) == (right["name"], right["type"], right.get("hints")),
                "Only description may change with Accept-Language; name, type and hints stay language-neutral")
        if left["type"] == "builtin":
            require(left["description"] != right["description"], f"Builtin description is not localized: {left['name']}")
        else:
            require(left["description"] == right["description"], f"Skill description must be returned as authored: {left['name']}")


def validate_projection_pair(runtime, public):
    validate_catalog_examples(runtime)
    validate_catalog_examples(public)
    left, right = success_examples(runtime), success_examples(public)
    for identity in left:
        require(left[identity]["bodies"] == right[identity]["bodies"], "Mate GET projection drifted from Runtime")

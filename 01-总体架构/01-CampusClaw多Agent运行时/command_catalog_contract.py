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


def validate_commands(commands, state):
    require(state in {"running", "idle"}, "Unexpected example state")
    require(isinstance(commands, list), "Commands must be a non-null list")
    for command in commands:
        validate_descriptor(command)
    names = [command["name"] for command in commands]
    require(len(names) == len(set(names)), "Duplicate command")
    builtin_names = [name for name in BUILTINS if state == "idle" or name != "compact"]
    skills = [command for command in commands if command["type"] == "skill"]
    require(state == "idle" or not skills, "Running must omit Skill commands")
    require(names == builtin_names + sorted(command["name"] for command in skills),
            "Command order or state filtering differs")
    for command in commands:
        name = command["name"]
        if name == "help":
            require(command["description"] == "介绍当前 Agent 的用途和使用场景", "Help must remain Agent guide")


def success_examples(operation):
    successes = [response for response in operation["responses"] if response["status"] == "200"]
    require(len(successes) == 2 and {response.get("id") for response in successes} == {"200-running", "200-idle"},
            "Both running and idle examples are required exactly once")
    return {response["id"]: response for response in successes}


def validate_catalog_examples(operation):
    for identity, response in success_examples(operation).items():
        require(response["headers"].get("Cache-Control") == "no-store", "GET must not cache mutable catalog")
        body = response["bodies"]["zh-CN"]
        require(set(body) == {"resCode", "resMsg", "result"} and body["resCode"] == "0"
                and body["resMsg"] == "success" and set(body["result"]) == {"commands"},
                "Catalog ResultBean differs")
        validate_commands(body["result"]["commands"], identity.removeprefix("200-"))
    examples = success_examples(operation)
    idle = {c["name"]: c for c in examples["200-idle"]["bodies"]["zh-CN"]["result"]["commands"]}
    for command in examples["200-running"]["bodies"]["zh-CN"]["result"]["commands"]:
        require(command == idle[command["name"]], "Descriptor metadata must not encode running permissions")


def validate_projection_pair(runtime, public):
    validate_catalog_examples(runtime)
    validate_catalog_examples(public)
    left, right = success_examples(runtime), success_examples(public)
    for identity in left:
        require(left[identity]["bodies"] == right[identity]["bodies"], "Mate GET projection drifted from Runtime")

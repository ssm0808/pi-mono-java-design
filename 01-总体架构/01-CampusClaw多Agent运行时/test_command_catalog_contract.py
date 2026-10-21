"""Design regression tests; these do not claim Runtime implementation coverage."""

import copy
import json
import unittest
from pathlib import Path

from command_catalog_contract import (validate_catalog_examples, validate_command_values, validate_commands,
                                      validate_descriptor)

ROOT = Path(__file__).resolve().parent
OPERATIONS = ROOT / "接口契约/操作"


class CommandCatalogContractTest(unittest.TestCase):
    def setUp(self):
        self.runtime = json.loads((OPERATIONS / "12-list-agent-commands.json").read_text())["operation"]
        self.idle = copy.deepcopy(self.runtime["responses"][0]["bodies"]["zh-CN"]["result"]["commands"])
        self.agent = copy.deepcopy(self.example("200-agent-commands")["bodies"]["zh-CN"]["result"]["commands"])

    def example(self, identity):
        return next(response for response in self.runtime["responses"] if response.get("id") == identity)

    def test_examples(self):
        validate_catalog_examples(self.runtime)

    def test_retired_fields_are_rejected(self):
        for field in ("kind", "input", "acceptsFiles", "acceptsArguments", "available",
                      "unavailableCode", "allowedValues", "catalogVersion", "snapshot", "argument", "hints",
                      "argumentOptional", "currentValue", "values", "placeholder"):
            with self.subTest(field=field):
                command = copy.deepcopy(self.idle[0])
                command[field] = True
                with self.assertRaises(RuntimeError):
                    validate_descriptor(command)

    def test_required_fields_and_types(self):
        for field in ("name", "type", "description"):
            for value in (None, "", [], 1):
                with self.subTest(field=field, value=value):
                    command = copy.deepcopy(self.idle[0])
                    command[field] = value
                    with self.assertRaises(RuntimeError):
                        validate_descriptor(command)
            command = copy.deepcopy(self.idle[0])
            del command[field]
            with self.assertRaises(RuntimeError):
                validate_descriptor(command)
        for command in ({"name": "model", "type": "skill", "description": "x"},
                        {"name": "skill:pdf", "type": "builtin", "description": "x"},
                        {"name": "name", "type": "builtin", "description": "x",
                         "argumentType": "text", "argumentRequired": True}):
            with self.subTest(command=command["name"]), self.assertRaises(RuntimeError):
                validate_descriptor(command)

    def test_argument_type_follows_the_command(self):
        by_name = {command["name"]: command for command in self.idle}
        self.assertEqual({name: command.get("argumentType") for name, command in by_name.items()},
                         {"help": None, "status": None, "rename": "text", "model": "options", "thinking": "options",
                          "mode": "options", "compact": None, "skills": None, "skill:pdf": "text"})
        invalid = (
            ("help", "argumentType", "text"),
            ("skill:pdf", "argumentType", "options"),
            ("rename", "argumentType", "options"),
            ("thinking", "argumentType", ["on", "off"]),
            ("model", "argumentHint", "<model>"),
            ("thinking", "hints", ["on", "off"]),
        )
        for name, field, value in invalid:
            with self.subTest(name=name, field=field):
                command = copy.deepcopy(by_name[name])
                command[field] = value
                with self.assertRaises(RuntimeError):
                    validate_descriptor(command)
        for name in ("rename", "model", "thinking", "mode", "skill:pdf"):
            with self.subTest(missing=name):
                command = copy.deepcopy(by_name[name])
                del command["argumentType"]
                with self.assertRaises(RuntimeError):
                    validate_descriptor(command)

    def test_argument_required_is_present_exactly_with_argument_type(self):
        by_name = {command["name"]: command for command in self.idle}
        self.assertEqual({name: command.get("argumentRequired") for name, command in by_name.items()},
                         {"help": None, "status": None, "rename": True, "model": True, "thinking": True,
                          "mode": True, "compact": None, "skills": None, "skill:pdf": False})
        invalid = (
            ("help", "argumentRequired", False),
            ("compact", "argumentRequired", True),
            ("rename", "argumentRequired", False),
            ("model", "argumentRequired", "true"),
            ("mode", "argumentRequired", None),
            ("skill:pdf", "argumentRequired", True),
            ("skill:pdf", "argumentRequired", 0),
        )
        for name, field, value in invalid:
            with self.subTest(name=name, value=value):
                command = copy.deepcopy(by_name[name])
                command[field] = value
                with self.assertRaises(RuntimeError):
                    validate_descriptor(command)
        for name in ("rename", "model", "thinking", "mode", "skill:pdf"):
            with self.subTest(missing=name):
                command = copy.deepcopy(by_name[name])
                del command["argumentRequired"]
                with self.assertRaises(RuntimeError):
                    validate_descriptor(command)

    def test_catalog_is_not_filtered_by_session_state(self):
        for name in ("compact", "mode"):
            with self.subTest(name=name):
                with self.assertRaises(RuntimeError):
                    validate_commands([command for command in self.idle if command["name"] != name])
        validate_commands([command for command in self.idle if command["type"] != "skill"])
        self.runtime["responses"][2]["bodies"]["zh-CN"]["result"]["commands"][4]["argumentType"] = "text"
        with self.assertRaises(RuntimeError):
            validate_catalog_examples(self.runtime)

    def test_session_id_selects_catalog_scope(self):
        expected = [command for command in self.idle
                    if command["type"] == "skill" or command["name"] not in ("status", "compact")]
        self.assertEqual(self.agent, expected)
        self.assertEqual([command["name"] for command in self.agent],
                         ["help", "rename", "model", "thinking", "mode", "skills", "skill:pdf"])
        validate_commands(self.agent, "agent")
        validate_commands([command for command in self.agent if command["type"] == "builtin"], "agent")
        by_name = {command["name"]: command for command in self.idle}
        swapped = [self.agent[1], self.agent[0]] + self.agent[2:]
        with_status = self.agent[:1] + [by_name["status"]] + self.agent[1:]
        with_compact = self.agent[:5] + [by_name["compact"]] + self.agent[5:]
        for commands in (self.idle, self.agent[1:], swapped, with_status, with_compact,
                         [command for command in self.agent if command["name"] != "model"]):
            with self.subTest(commands=[command["name"] for command in commands]), self.assertRaises(RuntimeError):
                validate_commands(commands, "agent")
        with self.assertRaises(RuntimeError):
            validate_commands(self.agent)
        mutations = (
            lambda op: self.pop_command(op, "200-agent-commands", "en-US", -1),
            lambda op: self.pop_command(op, "200-agent-commands", "zh-CN", 1),
            lambda op: op.update(parameters=[p for p in op["parameters"] if p.get("name") != "sessionId"]),
            lambda op: op.update(responses=[r for r in op["responses"] if r.get("id") != "200-agent-commands"]),
        )
        for mutate in mutations:
            self.setUp()
            mutate(self.runtime)
            with self.subTest(mutate=mutate), self.assertRaises(RuntimeError):
                validate_catalog_examples(self.runtime)

    @staticmethod
    def pop_command(operation, identity, language, index):
        response = next(item for item in operation["responses"] if item.get("id") == identity)
        response["bodies"][language]["result"]["commands"].pop(index)

    def test_only_builtin_description_follows_accept_language(self):
        def english(index):
            return self.runtime["responses"][0]["bodies"]["en-US"]["result"]["commands"][index]
        cases = (
            ("untranslated Builtin", lambda: english(0).update(description=self.idle[0]["description"])),
            ("translated Skill", lambda: english(-1).update(description="Analyze and generate PDF documents")),
            ("argumentType changed in one language", lambda: english(4).update(argumentType="text")),
            ("argumentType dropped in one language", lambda: english(5).pop("argumentType")),
            ("argumentRequired changed in one language", lambda: english(-1).update(argumentRequired=True)),
            ("argumentRequired dropped in one language", lambda: english(2).pop("argumentRequired")),
            ("missing en-US", lambda: self.runtime["responses"][0]["bodies"].pop("en-US")),
        )
        for label, mutate in cases:
            with self.subTest(case=label):
                self.setUp()
                mutate()
                with self.assertRaises(RuntimeError):
                    validate_catalog_examples(self.runtime)

    def test_order_duplicates_and_complete_empty_skills(self):
        validate_commands(self.idle[:-1])
        for commands in (list(reversed(self.idle)), self.idle + [self.idle[0]], self.idle[1:]):
            with self.assertRaises(RuntimeError):
                validate_commands(commands)
        skill = copy.deepcopy(self.idle[-1])
        skill["name"] = "skill:alpha"
        validate_commands(self.idle[:-1] + [skill, self.idle[-1]])
        with self.assertRaises(RuntimeError):
            validate_commands(self.idle + [skill])
        renamed = copy.deepcopy(self.idle)
        renamed[2]["name"] = "name"
        with self.assertRaises(RuntimeError):
            validate_commands(renamed)

    def test_missing_state_example_and_error_drift(self):
        self.runtime["responses"] = self.runtime["responses"][1:]
        with self.assertRaises(RuntimeError):
            validate_catalog_examples(self.runtime)
        for identity in ("400-invalid-agent-id", "404-agent-not-found", "422-agent-not-available"):
            self.setUp()
            self.runtime["responses"] = [r for r in self.runtime["responses"] if r.get("id") != identity]
            with self.subTest(identity=identity), self.assertRaises(RuntimeError):
                validate_catalog_examples(self.runtime)
        self.setUp()
        self.runtime["responses"].append({"id": "503-agent-not-available", "status": "503",
                                          "bodies": {"zh-CN": {"resCode": "AGENT_NOT_AVAILABLE", "resMsg": "x"}}})
        with self.assertRaises(RuntimeError):
            validate_catalog_examples(self.runtime)


class CommandValuesContractTest(unittest.TestCase):
    def setUp(self):
        self.values = json.loads((OPERATIONS / "09-list-agent-command-values.json").read_text())["operation"]
        create = json.loads((OPERATIONS / "01-create-session.json").read_text())["operation"]
        created = next(item for item in create["responses"] if item["status"] == "201")
        self.created = next(iter(created["bodies"].values()))["result"]

    def response(self, operation, identity):
        return next(item for item in operation["responses"] if item.get("id") == identity)

    def result(self, operation, identity):
        return self.response(operation, identity)["bodies"]["en-US"]["result"]

    def reject(self, mutate, created=None):
        broken = copy.deepcopy(self.values)
        mutate(broken)
        with self.assertRaises(RuntimeError):
            validate_command_values(broken, created or self.created)

    def test_one_values_query_serves_every_option_command(self):
        validate_command_values(self.values, self.created)
        for mutate in (lambda op: op["parameters"][1].update(schema="model | thinking"),
                       lambda op: op["parameters"][1].update(schema="rename | model | thinking | mode"),
                       lambda op: op["responses"].pop(4),
                       lambda op: self.result(op, "200-model")["values"].clear(),
                       lambda op: self.result(op, "200-thinking")["values"].pop(),
                       lambda op: self.result(op, "200-thinking-unsupported")["values"].append("on"),
                       lambda op: self.result(op, "200-thinking").update(label="On"),
                       lambda op: self.result(op, "200-model-empty").update(currentValue="other")):
            with self.subTest(mutate=mutate):
                self.reject(mutate)

    def test_values_are_queried_per_agent_with_optional_session(self):
        self.reject(lambda op: op.update(path="/sessions/{sessionId}/commands/{commandName}/values"))
        self.reject(lambda op: op.update(parameters=[p for p in op["parameters"] if p.get("name") != "sessionId"]))
        self.reject(lambda op: next(p for p in op["parameters"] if p.get("name") == "sessionId").update(required=True))

    def test_sessionless_examples_return_the_new_session_initial_values(self):
        for identity in ("200-model-agent", "200-thinking-agent", "200-mode-agent"):
            with self.subTest(missing=identity):
                self.reject(lambda op: op["responses"].remove(self.response(op, identity)))
            with self.subTest(scope=identity):
                self.reject(lambda op: self.response(op, identity).update(summary="带 sessionId：错误的范围。"))
        self.reject(lambda op: self.result(op, "200-model-agent").update(currentValue="model_other"))
        self.reject(lambda op: self.result(op, "200-model-agent")["values"].pop())
        self.reject(lambda op: self.result(op, "200-thinking-agent").update(values=["off"], currentValue="off"))
        self.reject(lambda op: self.result(op, "200-mode-agent").update(currentValue="plan"))
        self.reject(lambda op: self.response(op, "200-model").update(summary="不带 sessionId：错误的范围。"))
        self.reject(lambda op: None, created={**self.created, "modelId": "model_other"})
        self.reject(lambda op: None, created={**self.created, "mode": "plan"})

    def test_agent_errors_are_documented_exactly(self):
        for identity in ("400-invalid-agent-id", "404-agent-not-found", "422-agent-not-available",
                         "404-command-values-not-found", "404-session-not-found"):
            with self.subTest(identity=identity):
                self.reject(lambda op: op["responses"].remove(self.response(op, identity)))
        self.reject(lambda op: op["responses"].append(
            {"id": "503-agent-not-available", "status": "503",
             "bodies": {"en-US": {"resCode": "AGENT_NOT_AVAILABLE", "resMsg": "x"}}}))


if __name__ == "__main__":
    unittest.main()

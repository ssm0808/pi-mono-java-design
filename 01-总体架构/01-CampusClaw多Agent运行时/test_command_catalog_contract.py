"""Design regression tests; these do not claim Runtime implementation coverage."""

import copy
import json
import unittest
from pathlib import Path

from command_catalog_contract import validate_catalog_examples, validate_commands, validate_descriptor, validate_projection_pair

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT.parents[1] / "02-服务与接口/06-mate-service聊天命令API"


class CommandCatalogContractTest(unittest.TestCase):
    def setUp(self):
        self.runtime = json.loads((ROOT / "接口契约/操作/12-list-agent-commands.json").read_text())["operation"]
        self.public = json.loads((PUBLIC / "接口契约/操作/01-list-chat-commands.json").read_text())["operation"]
        self.idle = copy.deepcopy(self.runtime["responses"][0]["bodies"]["zh-CN"]["result"]["commands"])

    def test_both_projections_and_examples(self):
        validate_projection_pair(self.runtime, self.public)

    def test_retired_fields_are_rejected(self):
        for field in ("kind", "input", "acceptsFiles", "acceptsArguments", "available",
                      "unavailableCode", "allowedValues", "catalogVersion", "snapshot", "argument", "hints"):
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
                        {"name": "skill:pdf", "type": "builtin", "description": "x"}):
            with self.assertRaises(RuntimeError):
                validate_descriptor(command)

    def test_argument_hint_is_a_placeholder_not_values(self):
        by_name = {command["name"]: command for command in self.idle}
        self.assertEqual({name: command.get("argumentHint") for name, command in by_name.items()},
                         {"help": None, "status": None, "name": "<name>", "model": "<model>", "thinking": "<level>",
                          "mode": "<mode>", "compact": None, "skills": None, "skill:pdf": None})
        invalid = (
            ("help", "<x>"),
            ("skill:pdf", "<task>"),
            ("thinking", "<on|off>"),
            ("thinking", ["on", "off"]),
            ("mode", ["plan", "build"]),
            ("model", "选择模型"),
        )
        for name, hint in invalid:
            with self.subTest(name=name, hint=hint):
                command = copy.deepcopy(by_name[name])
                command["argumentHint"] = hint
                with self.assertRaises(RuntimeError):
                    validate_descriptor(command)
        for name in ("name", "model", "thinking", "mode"):
            with self.subTest(missing=name):
                command = copy.deepcopy(by_name[name])
                del command["argumentHint"]
                with self.assertRaises(RuntimeError):
                    validate_descriptor(command)

    def test_catalog_is_not_filtered_by_session_state(self):
        for name in ("compact", "mode"):
            with self.subTest(name=name):
                with self.assertRaises(RuntimeError):
                    validate_commands([command for command in self.idle if command["name"] != name])
        validate_commands([command for command in self.idle if command["type"] != "skill"])
        examples = self.runtime["responses"]
        examples[2]["bodies"]["zh-CN"]["result"]["commands"][4]["argumentHint"] = "<x>"
        with self.assertRaises(RuntimeError):
            validate_catalog_examples(self.runtime)

    def test_session_id_selects_catalog_scope(self):
        agent = [command for command in self.idle if command["type"] == "skill" or command["name"] in ("help", "skills")]
        validate_commands(agent, "agent")
        validate_commands([command for command in agent if command["type"] == "builtin"], "agent")
        session_only = next(command for command in self.idle if command["name"] == "status")
        for commands in (self.idle, agent[1:], [agent[1], agent[0]] + agent[2:], agent[:1] + [session_only] + agent[1:]):
            with self.subTest(commands=[command["name"] for command in commands]), self.assertRaises(RuntimeError):
                validate_commands(commands, "agent")
        with self.assertRaises(RuntimeError):
            validate_commands(agent)
        examples = {response.get("id"): response for response in self.runtime["responses"]}
        examples["200-agent-commands"]["bodies"]["en-US"]["result"]["commands"].pop()
        with self.assertRaises(RuntimeError):
            validate_catalog_examples(self.runtime)
        self.setUp()
        self.runtime["parameters"] = [p for p in self.runtime["parameters"] if p.get("name") != "sessionId"]
        with self.assertRaises(RuntimeError):
            validate_catalog_examples(self.runtime)
        self.setUp()
        self.public["responses"].insert(1, next(r for r in self.runtime["responses"] if r.get("id") == "200-agent-commands"))
        self.public["parameters"] = self.runtime["parameters"]
        with self.assertRaises(RuntimeError):
            validate_projection_pair(self.runtime, self.public)

    def test_only_builtin_description_follows_accept_language(self):
        def english(index):
            return self.runtime["responses"][0]["bodies"]["en-US"]["result"]["commands"][index]
        cases = (
            ("untranslated Builtin", lambda: english(0).update(description=self.idle[0]["description"])),
            ("translated Skill", lambda: english(-1).update(description="Analyze and generate PDF documents")),
            ("argumentHint translated", lambda: english(4).update(argumentHint="<级别>")),
            ("argumentHint dropped in one language", lambda: english(5).pop("argumentHint")),
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

    def test_public_argument_type_follows_mate_mapping(self):
        commands = {command["name"]: command for command in
                    self.public["responses"][0]["bodies"]["en-US"]["result"]["commands"]}
        self.assertEqual({name: command.get("argumentType") for name, command in commands.items()},
                         {"help": None, "status": None, "name": "text", "model": "options", "thinking": "options",
                          "mode": "options", "compact": None, "skills": None, "skill:pdf": "text"})
        for mutate in (lambda: commands["model"].pop("argumentType"),
                       lambda: commands["help"].update(argumentType="text"),
                       lambda: commands["skill:pdf"].update(argumentType="options")):
            with self.subTest(mutate=mutate):
                self.setUp()
                commands = {command["name"]: command for command in
                            self.public["responses"][0]["bodies"]["en-US"]["result"]["commands"]}
                mutate()
                with self.assertRaises(RuntimeError):
                    validate_projection_pair(self.runtime, self.public)
        with self.assertRaises(RuntimeError):
            validate_descriptor(dict(self.idle[3], argumentType="options"))

    def test_missing_state_example_and_cross_boundary_drift(self):
        self.runtime["responses"] = self.runtime["responses"][1:]
        with self.assertRaises(RuntimeError):
            validate_catalog_examples(self.runtime)
        self.setUp()
        self.public["responses"][1]["bodies"]["zh-CN"]["result"]["commands"][-1]["description"] = "different"
        with self.assertRaises(RuntimeError):
            validate_projection_pair(self.runtime, self.public)


if __name__ == "__main__":
    unittest.main()

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
                      "unavailableCode", "allowedValues", "catalogVersion", "snapshot", "argument"):
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

    def test_hints_list_fixed_submit_values(self):
        by_name = {command["name"]: command for command in self.idle}
        self.assertEqual(by_name["thinking"]["hints"], ["on", "off"])
        self.assertEqual(by_name["mode"]["hints"], ["plan", "build"])
        invalid = (
            ("help", ["x"]),
            ("name", ["新的会话名称"]),
            ("model", ["gpt"]),
            ("skill:pdf", ["说明要处理的内容"]),
            ("thinking", ["on"]),
            ("thinking", ["开启", "关闭"]),
            ("thinking", [{"value": "on", "label": "开启"}, {"value": "off", "label": "关闭"}]),
            ("mode", ["build", "plan"]),
            ("mode", []),
        )
        for name, hints in invalid:
            with self.subTest(name=name, hints=hints):
                command = copy.deepcopy(by_name[name])
                command["hints"] = hints
                with self.assertRaises(RuntimeError):
                    validate_descriptor(command)
        for name in ("thinking", "mode"):
            with self.subTest(missing=name):
                command = copy.deepcopy(by_name[name])
                del command["hints"]
                with self.assertRaises(RuntimeError):
                    validate_descriptor(command)

    def test_catalog_is_not_filtered_by_session_state(self):
        for name in ("compact", "mode"):
            with self.subTest(name=name):
                with self.assertRaises(RuntimeError):
                    validate_commands([command for command in self.idle if command["name"] != name])
        validate_commands([command for command in self.idle if command["type"] != "skill"])
        examples = self.runtime["responses"]
        examples[1]["bodies"]["zh-CN"]["result"]["commands"][4]["hints"] = ["x"]
        with self.assertRaises(RuntimeError):
            validate_catalog_examples(self.runtime)

    def test_only_builtin_description_follows_accept_language(self):
        def english(index):
            return self.runtime["responses"][0]["bodies"]["en-US"]["result"]["commands"][index]
        cases = (
            ("untranslated Builtin", lambda: english(0).update(description=self.idle[0]["description"])),
            ("translated Skill", lambda: english(-1).update(description="Analyze and generate PDF documents")),
            ("hint value translated", lambda: english(4).update(hints=["开启", "关闭"])),
            ("hints dropped in one language", lambda: english(5).pop("hints")),
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

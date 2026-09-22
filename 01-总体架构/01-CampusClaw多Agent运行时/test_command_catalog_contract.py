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
        self.runtime = json.loads((ROOT / "接口契约/操作/12-list-session-commands.json").read_text())["operation"]
        self.public = json.loads((PUBLIC / "接口契约/操作/01-list-chat-commands.json").read_text())["operation"]
        self.running = copy.deepcopy(self.runtime["responses"][0]["bodies"]["zh-CN"]["result"]["commands"])
        self.idle = copy.deepcopy(self.runtime["responses"][1]["bodies"]["zh-CN"]["result"]["commands"])

    def test_both_projections_and_examples(self):
        validate_projection_pair(self.runtime, self.public)

    def test_retired_fields_are_rejected(self):
        for field in ("kind", "input", "acceptsFiles", "acceptsArguments", "available",
                      "unavailableCode", "allowedValues", "catalogVersion", "snapshot"):
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

    def test_hints_are_optional_display_text_not_capabilities(self):
        for original in (self.idle[2], self.idle[-1]):
            for hints in ([], ["request"], ["显示提示", "任意展示文字"]):
                command = copy.deepcopy(original)
                command["hints"] = hints
                validate_descriptor(command)
            del command["hints"]
            validate_descriptor(command)
        for value in (None, {}, "modelId", [None], [1], [""], ["  "], [{"value": "x"}]):
            with self.subTest(value=value):
                command = copy.deepcopy(self.idle[-1])
                command["hints"] = value
                with self.assertRaises(RuntimeError):
                    validate_descriptor(command)

    def test_running_filters_commands_but_keeps_metadata(self):
        for name in ("compact", "skill:pdf"):
            commands = self.running + [next(command for command in self.idle if command["name"] == name)]
            with self.assertRaises(RuntimeError):
                validate_commands(commands, "running")
        for name in ("model", "thinking"):
            running = next(command for command in self.running if command["name"] == name)
            idle = next(command for command in self.idle if command["name"] == name)
            self.assertEqual(running, idle)
        commands = self.runtime["responses"][0]["bodies"]["zh-CN"]["result"]["commands"]
        next(command for command in commands if command["name"] == "model")["hints"] = []
        with self.assertRaises(RuntimeError):
            validate_catalog_examples(self.runtime)

    def test_order_duplicates_and_complete_empty_skills(self):
        validate_commands(self.idle[:-1], "idle")
        for commands in (list(reversed(self.idle)), self.idle + [self.idle[0]], self.idle[1:]):
            with self.assertRaises(RuntimeError):
                validate_commands(commands, "idle")
        skill = copy.deepcopy(self.idle[-1])
        skill["name"] = "skill:alpha"
        validate_commands(self.idle[:-1] + [skill, self.idle[-1]], "idle")
        with self.assertRaises(RuntimeError):
            validate_commands(self.idle + [skill], "idle")

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

"""Design regression tests; these do not claim Runtime implementation coverage."""

import copy
import json
import unittest
from pathlib import Path

from command_catalog_contract import validate_catalog_examples, validate_commands, validate_projection_pair

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

    def test_all_legacy_and_replacement_fields_are_rejected(self):
        for field in ("available", "unavailableCode", "allowedValues", "catalogVersion", "snapshot"):
            with self.subTest(field=field):
                commands = copy.deepcopy(self.idle)
                commands[0][field] = True
                with self.assertRaises(RuntimeError):
                    validate_commands(commands, "idle")
        for field in ("mode", "available", "unavailableCode", "placeholder", "suggestions", "allowedValues"):
            with self.subTest(field=field):
                commands = copy.deepcopy(self.idle)
                commands[2]["input"][field] = []
                with self.assertRaises(RuntimeError):
                    validate_commands(commands, "idle")

    def test_required_fields_and_types(self):
        for field in ("name", "kind", "description"):
            for value in (None, "", [], 1):
                with self.subTest(field=field, value=value):
                    commands = copy.deepcopy(self.idle)
                    commands[0][field] = value
                    with self.assertRaises(RuntimeError):
                        validate_commands(commands, "idle")
            commands = copy.deepcopy(self.idle)
            del commands[0][field]
            with self.assertRaises(RuntimeError):
                validate_commands(commands, "idle")

    def test_input_omission_and_true_only(self):
        for value in (None, {}, {"hint": ""}, {"hint": "  "}, {"hint": 1},
                      {"hint": "[request]", "acceptsFiles": False},
                      {"hint": "[request]", "acceptsFiles": 1}):
            with self.subTest(value=value):
                commands = copy.deepcopy(self.idle)
                commands[-1]["input"] = value
                with self.assertRaises(RuntimeError):
                    validate_commands(commands, "idle")
        for name in ("help", "status", "compact", "skills"):
            commands = copy.deepcopy(self.idle)
            next(command for command in commands if command["name"] == name)["input"] = {"hint": "[command]"}
            with self.assertRaises(RuntimeError):
                validate_commands(commands, "idle")

    def test_running_filter_and_query_only(self):
        for name in ("compact", "skill:pdf"):
            commands = self.running + [next(command for command in self.idle if command["name"] == name)]
            with self.assertRaises(RuntimeError):
                validate_commands(commands, "running")
        for name in ("model", "thinking"):
            commands = copy.deepcopy(self.running)
            next(command for command in commands if command["name"] == name)["input"] = {"hint": "[value]"}
            with self.assertRaises(RuntimeError):
                validate_commands(commands, "running")

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

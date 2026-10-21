#!/usr/bin/env python3
"""Regression checks for the source-derived Help page and Runtime-only command tooling."""

import copy
import unittest
from pathlib import Path

from help_review_projection import HELP_ERROR_IDS, project_help_model
from render_chat_http_v1 import load_contract

ROOT = Path(__file__).resolve().parent
RETIRED_MATE_TOPIC = "06-mate-service聊天命令API"


class DocumentMaintenanceTest(unittest.TestCase):
    def setUp(self):
        _, models = load_contract()
        self.runtime = next(m for m in models if m["operation"]["operationKey"] == "ExecuteSessionCommand")

    def test_help_follows_canonical_values_and_parameters(self):
        source = copy.deepcopy(self.runtime)
        source["api"]["version"] = "test-version"
        operation = source["operation"]
        builtin = next(mode for mode in operation["requestHeaderExamples"] if mode["id"] == "builtin")
        builtin["headers"][0]["description"] = "测试源说明"
        operation["parameters"][0]["description"] = "测试路径说明"
        operation["requestBody"]["description"] = "测试请求说明"
        operation["responses"][0]["bodies"]["zh-CN"]["result"]["text"] = "## 测试助手\n\n测试介绍"
        projected = project_help_model(source)
        self.assertEqual(projected["api"]["version"], "test-version")
        self.assertEqual(projected["operation"]["parameters"], operation["parameters"])
        self.assertEqual(projected["operation"]["requestHeaderExamples"], [builtin])
        self.assertEqual(projected["operation"]["requestBody"]["description"], "测试请求说明")
        self.assertEqual(projected["operation"]["responses"][0], operation["responses"][0])

    def test_help_projection_does_not_mutate_source(self):
        original = copy.deepcopy(self.runtime)
        projected = project_help_model(self.runtime)
        projected["operation"]["requestHeaderExamples"].clear()
        projected["operation"]["responses"][0]["bodies"].clear()
        self.assertEqual(self.runtime, original)

    def test_help_selects_only_help_and_existing_errors(self):
        view = project_help_model(self.runtime)["operation"]
        self.assertEqual({r["id"] for r in view["responses"]},
                         {"200-help", "200-help-empty"} | HELP_ERROR_IDS)
        self.assertEqual(view["requestBody"]["example"], {"name": "help"})
        self.assertEqual(len(view["requestBody"]["examples"]), 1)

    def test_missing_canonical_help_data_fails_closed(self):
        source = copy.deepcopy(self.runtime)
        source["operation"]["requestHeaderExamples"] = [
            mode for mode in source["operation"]["requestHeaderExamples"] if mode["id"] != "builtin"]
        with self.assertRaisesRegex(ValueError, "Builtin Header"):
            project_help_model(source)
        for identity in {"200-help", "200-help-empty"} | HELP_ERROR_IDS:
            source = copy.deepcopy(self.runtime)
            source["operation"]["responses"] = [r for r in source["operation"]["responses"]
                                                if r["id"] != identity]
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                project_help_model(source)
        source = copy.deepcopy(self.runtime)
        source["operation"]["requestBody"]["examples"] = []
        with self.assertRaises(ValueError):
            project_help_model(source)

    def test_help_projection_is_text_only(self):
        view = project_help_model(self.runtime)["operation"]
        for response in view["responses"]:
            if response["status"] == "200":
                for body in response["bodies"].values():
                    self.assertEqual(set(body["result"]), {"text"})
        self.assertIn("Markdown", view["description"])

    def test_runtime_tooling_does_not_depend_on_retired_mate_command_topic(self):
        for path in sorted(ROOT.glob("*.py")) + sorted(ROOT.glob("*.cjs")):
            if path.name == Path(__file__).name:
                continue
            with self.subTest(path=path.name):
                self.assertNotIn(RETIRED_MATE_TOPIC, path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Regression checks for source-derived Help and retired Mate Command artifacts."""

import copy
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from help_review_projection import HELP_ERROR_IDS, project_help_model
from render_chat_http_v1 import load_contract

ROOT = Path(__file__).resolve().parent
MATE_ROOT = ROOT.parents[1] / "02-服务与接口/06-mate-service聊天命令API"
sys.path.insert(0, str(MATE_ROOT))
SPEC = importlib.util.spec_from_file_location("mate_command_gate", MATE_ROOT / "validate-chat-command-v1.py")
MATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MATE)


class DocumentMaintenanceTest(unittest.TestCase):
    def setUp(self):
        _, models = load_contract()
        self.runtime = next(m for m in models if m["operation"]["operationKey"] == "executeSessionCommand")

    def test_help_follows_canonical_values_and_parameters(self):
        source = copy.deepcopy(self.runtime)
        source["api"]["version"] = "test-version"
        operation = source["operation"]
        builtin = next(mode for mode in operation["requestHeaderExamples"] if mode["id"] == "builtin")
        builtin["headers"][0]["description"] = "测试源说明"
        operation["parameters"][0]["description"] = "测试路径说明"
        operation["requestBody"]["description"] = "测试请求说明"
        operation["responses"][0]["bodies"]["zh-CN"]["result"]["description"] = ["测试介绍"]
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

    def test_mate_only_retains_get_without_approving_public_boundary(self):
        common, models = MATE.load_contract()
        MATE.validate_contract(common, models)
        MATE.validate_retirement()
        self.assertEqual(len(models), 1)
        extra = copy.deepcopy(models[0])
        extra["operation"]["method"] = "POST"
        with self.assertRaises(RuntimeError):
            MATE.validate_contract(common, models + [extra])
        common["api"]["visibility"] = "Public · 已确认"
        with self.assertRaises(RuntimeError):
            MATE.validate_contract(common, models)

    def test_retired_mate_files_cannot_return(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            operations = root / "接口契约/操作"
            operations.mkdir(parents=True)
            (operations / "01-list-chat-commands.json").touch()
            MATE.validate_retirement(root)
            for relative in ("接口契约/操作/02-execute-chat-command.json", "设计图/diagram.puml",
                             "设计图/public_command_boundary.svg", "设计图/public_sse_projection.svg"):
                retired = root / relative
                retired.parent.mkdir(parents=True, exist_ok=True)
                retired.touch()
                with self.subTest(path=relative), self.assertRaises(RuntimeError):
                    MATE.validate_retirement(root)
                retired.unlink()


if __name__ == "__main__":
    unittest.main()

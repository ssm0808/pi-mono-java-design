#!/usr/bin/env python3
"""Negative tests for the confirmed Help design gate, not Runtime implementation tests."""

import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("contract_validator", ROOT / "validate-chat-http-v1.py")
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


class HelpContractTest(unittest.TestCase):
    def setUp(self):
        _, models = GATE.load_contract()
        operations = {model["operation"]["operationKey"]: model["operation"] for model in models}
        self.operation = operations["ExecuteSessionCommand"]
        commands = operations["ListAgentCommands"]["responses"][0]["bodies"]["zh-CN"]["result"]["commands"]
        self.descriptor = next(command for command in commands if command["name"] == "help")
        self.body = GATE.help_successes(self.operation)["200-help"]["bodies"]["zh-CN"]
        self.projection = GATE.load_help_model()

    def test_confirmed_contract(self):
        GATE.validate_help_descriptor(self.descriptor)
        GATE.validate_help_operation(self.operation)
        GATE.validate_help_projection(self.projection, self.operation)

    def test_descriptor_rejects_old_parameter_entry(self):
        for field, value in (("mode", "optional"), ("available", True),
                             ("unavailableCode", None), ("acceptsFiles", True),
                             ("placeholder", "command"), ("suggestions", ["model"])):
            with self.subTest(field=field):
                descriptor = copy.deepcopy(self.descriptor)
                descriptor["input"] = {field: value}
                with self.assertRaises(RuntimeError):
                    GATE.validate_help_descriptor(descriptor)

    def test_descriptor_takes_no_argument(self):
        for field, value in (("argumentType", "text"), ("argumentRequired", False)):
            with self.subTest(field=field):
                descriptor = copy.deepcopy(self.descriptor)
                descriptor[field] = value
                with self.assertRaises(RuntimeError):
                    GATE.validate_help_descriptor(descriptor)

    def test_result_rejects_legacy_and_private_fields(self):
        for field in ("command", "changed", "commands", "systemPrompt", "agentId", "version", "path",
                      "bindingSkills", "bindingTools", "userCases", "sourceEventSeq",
                      "displayName", "description", "useCases"):
            with self.subTest(field=field):
                body = copy.deepcopy(self.body)
                body["result"][field] = "not-public"
                with self.assertRaises(RuntimeError):
                    GATE.validate_help_body(body)

    def test_result_is_only_text(self):
        self.assertEqual(GATE.HELP_RESULT_FIELDS, {"text"})
        body = copy.deepcopy(self.body)
        del body["result"]["text"]
        with self.assertRaises(RuntimeError):
            GATE.validate_help_body(body)
        body = copy.deepcopy(self.body)
        body["result"] = {"displayName": "园区网络分析助手", "description": ["介绍"], "useCases": ["场景"]}
        with self.assertRaises(RuntimeError):
            GATE.validate_help_body(body)

    def test_text_is_nonblank_trimmed_markdown(self):
        for value in (None, "", "  ", 7, [], ["## Agent"], {"text": "## Agent"}, " ## Agent ", "## Agent\n"):
            with self.subTest(value=value):
                body = copy.deepcopy(self.body)
                body["result"]["text"] = value
                with self.assertRaises(RuntimeError):
                    GATE.validate_help_body(body)

    def test_text_starts_with_agent_display_name_heading(self):
        for value in ("园区网络分析助手", "# 园区网络分析助手", "##   ", "介绍\n\n## 园区网络分析助手"):
            with self.subTest(value=value):
                body = copy.deepcopy(self.body)
                body["result"]["text"] = value
                with self.assertRaises(RuntimeError):
                    GATE.validate_help_body(body)
        body = copy.deepcopy(self.body)
        body["result"]["text"] = "## 园区网络分析助手\n\n暂无介绍。"
        GATE.validate_help_body(body)

    def test_empty_response_and_no_argument_request_are_required(self):
        operation = copy.deepcopy(self.operation)
        operation["responses"] = [r for r in operation["responses"] if r["id"] != "200-help-empty"]
        with self.assertRaises(RuntimeError):
            GATE.validate_help_operation(operation)
        for identity, text in (("200-help-empty", "## 园区网络分析助手\n\n- 场景"),
                               ("200-help", "## 园区网络分析助手\n\n暂无介绍。"),
                               ("200-help", "## 园区网络分析助手\n\n帮助理解园区网络状态。")):
            with self.subTest(identity=identity, text=text):
                operation = copy.deepcopy(self.operation)
                response = next(r for r in operation["responses"] if r["id"] == identity)
                response["bodies"]["zh-CN"]["result"]["text"] = text
                with self.assertRaises(RuntimeError):
                    GATE.validate_help_operation(operation)
        operation = copy.deepcopy(self.operation)
        operation["requestBody"]["examples"][0]["value"]["arguments"] = "model"
        with self.assertRaises(RuntimeError):
            GATE.validate_help_operation(operation)

    def test_projection_headers_cannot_keep_old_values_or_descriptions(self):
        for field, value in (("value", "Bearer <JWT>"), ("description", "公司调用方标识")):
            projection = copy.deepcopy(self.projection)
            projection["operation"]["requestHeaderExamples"][0]["headers"][0][field] = value
            with self.assertRaises(RuntimeError):
                GATE.validate_help_projection(projection, self.operation)

        projection = copy.deepcopy(self.projection)
        projection["operation"]["authModes"] = []
        with self.assertRaises(RuntimeError):
            GATE.validate_help_projection(projection, self.operation)

    def test_projection_cannot_drift_or_reopen_decisions(self):
        projection = copy.deepcopy(self.projection)
        projection["operation"]["responses"][0]["bodies"]["zh-CN"]["result"]["text"] = "## 其他助手"
        with self.assertRaises(RuntimeError):
            GATE.validate_help_projection(projection, self.operation)
        projection = copy.deepcopy(self.projection)
        projection["review"]["questions"] = [{"id": "reopen"}]
        with self.assertRaises(RuntimeError):
            GATE.validate_help_projection(projection, self.operation)


if __name__ == "__main__":
    unittest.main()

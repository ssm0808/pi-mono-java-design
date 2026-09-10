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
        self.operation = operations["executeSessionCommand"]
        commands = operations["listSessionCommands"]["responses"][0]["bodies"]["zh-CN"]["result"]["commands"]
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

    def test_result_rejects_legacy_and_private_fields(self):
        for field in ("command", "changed", "commands", "systemPrompt", "agentId", "version", "path",
                      "bindingSkills", "bindingTools", "useCases", "sourceEventSeq"):
            with self.subTest(field=field):
                body = copy.deepcopy(self.body)
                body["result"][field] = "not-public"
                with self.assertRaises(RuntimeError):
                    GATE.validate_help_body(body)

    def test_result_requires_all_three_fields(self):
        for field in GATE.HELP_RESULT_FIELDS:
            with self.subTest(field=field):
                body = copy.deepcopy(self.body)
                del body["result"][field]
                with self.assertRaises(RuntimeError):
                    GATE.validate_help_body(body)

    def test_arrays_are_strings_not_null_or_objects(self):
        for field in ("description", "userCases"):
            for value in (None, "text", {}, [None], [7], ["  "], [" text "], [{"text": "scene"}]):
                with self.subTest(field=field, value=value):
                    body = copy.deepcopy(self.body)
                    body["result"][field] = value
                    with self.assertRaises(RuntimeError):
                        GATE.validate_help_body(body)

    def test_empty_sections_remain_valid(self):
        for field in ("description", "userCases"):
            body = copy.deepcopy(self.body)
            body["result"][field] = []
            GATE.validate_help_body(body)
        body["result"]["description"] = []
        GATE.validate_help_body(body)

    def test_display_name_is_nonblank(self):
        for value in (None, "", "  ", 7):
            with self.subTest(value=value):
                body = copy.deepcopy(self.body)
                body["result"]["displayName"] = value
                with self.assertRaises(RuntimeError):
                    GATE.validate_help_body(body)

    def test_empty_response_and_no_argument_request_are_required(self):
        operation = copy.deepcopy(self.operation)
        operation["responses"] = [r for r in operation["responses"] if r["id"] != "200-help-empty"]
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
        projection["operation"]["responses"][0]["bodies"]["zh-CN"]["result"]["userCases"] = []
        with self.assertRaises(RuntimeError):
            GATE.validate_help_projection(projection, self.operation)
        projection = copy.deepcopy(self.projection)
        projection["review"]["questions"] = [{"id": "reopen"}]
        with self.assertRaises(RuntimeError):
            GATE.validate_help_projection(projection, self.operation)


if __name__ == "__main__":
    unittest.main()

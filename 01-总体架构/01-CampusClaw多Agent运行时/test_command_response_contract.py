#!/usr/bin/env python3
"""Negative tests for response design reuse, not implementation behavior."""

import copy
import unittest

from command_response_contract import RETIRED_FIELDS, SESSION_CASES, validate_response_reuse
from render_chat_http_v1 import load_contract


class CommandResponseContractTest(unittest.TestCase):
    def setUp(self):
        _, self.models = load_contract()

    @staticmethod
    def operation(models, key="ExecuteSessionCommand"):
        return next(model["operation"] for model in models if model["operation"]["operationKey"] == key)

    def cases(self, models):
        return {item["id"]: item for item in self.operation(models)["responses"] if item["status"] == "200" and item["id"] != "200-skill-message"}

    @staticmethod
    def result(response):
        return response["bodies"]["zh-CN"]["result"]

    def reject(self, mutate):
        models = copy.deepcopy(self.models)
        mutate(self.cases(models))
        with self.assertRaises(RuntimeError):
            validate_response_reuse(models)

    def test_confirmed_response_reuse(self):
        validate_response_reuse(self.models)

    def test_mode_request_and_capability_error_cannot_disappear(self):
        for remove_error in (False, True):
            with self.subTest(remove_error=remove_error):
                models = copy.deepcopy(self.models)
                operation = self.operation(models)
                if remove_error:
                    operation["responses"] = [r for r in operation["responses"]
                                              if r["id"] != "422-plan-mode-unavailable"]
                else:
                    operation["requestBody"]["examples"] = [e for e in operation["requestBody"]["examples"]
                        if e["value"] != {"name": "mode", "arguments": "build"}]
                with self.assertRaises(RuntimeError):
                    validate_response_reuse(models)

    def test_retired_fields_rejected_for_every_success(self):
        for identity in self.cases(self.models):
            for field in RETIRED_FIELDS:
                with self.subTest(identity=identity, field=field):
                    self.reject(lambda cases: self.result(cases[identity]).update({field: "private"}))

    def test_session_cannot_be_a_command_specific_subset(self):
        for identity in SESSION_CASES:
            for field in ("sessionId", "agentId", "displayName", "modelId", "state", "thinking", "mode",
                          "lifetimeUsage", "createdAt", "updatedAt"):
                with self.subTest(identity=identity, field=field):
                    self.reject(lambda cases: self.result(cases[identity]).pop(field))

    def test_nested_usage_and_field_types_cannot_drift(self):
        self.reject(lambda cases: self.result(cases["200-status"])["lifetimeUsage"]["cost"].pop("total"))
        for field, value in (("state", 1), ("thinking", "on"), ("displayName", []), ("lifetimeUsage", None)):
            with self.subTest(field=field):
                self.reject(lambda cases: self.result(cases["200-status"]).update({field: value}))
        self.reject(lambda cases: self.result(cases["200-status"])["lifetimeUsage"].update({"input": True}))

    def test_cross_operation_source_shape_is_authoritative(self):
        models = copy.deepcopy(self.models)
        response = next(item for item in self.operation(models, "GetSession")["responses"] if item["status"] == "200")
        next(iter(response["bodies"].values()))["result"]["newResourceField"] = "example"
        with self.assertRaises(RuntimeError):
            validate_response_reuse(models)
        self.reject(lambda cases: self.result(cases["200-model-query"]).update({"newResourceField": "example"}))

    def test_headers_match_resource_kind(self):
        for identity in SESSION_CASES:
            with self.subTest(identity=identity):
                self.reject(lambda cases: cases[identity]["headers"].update({"ETag": '"retired"'}))
        self.reject(lambda cases: cases["200-model-query"]["headers"].update({"ETag": '"snp-extra"'}))
        self.reject(lambda cases: cases["200-status"]["headers"].update({"Content-Language": "en-US"}))
        self.reject(lambda cases: cases["200-status"]["headers"].update({"Cache-Control": "public"}))

    def test_query_and_mutation_examples_cannot_collapse(self):
        self.reject(lambda cases: self.result(cases["200-model"]).update(self.result(cases["200-model-query"])))
        self.reject(lambda cases: cases["200-model-query"].update({"id": "200-model"}))
        self.reject(lambda cases: self.result(cases["200-model"]).update({"state": "running"}))
        self.reject(lambda cases: self.result(cases["200-thinking-query"]).update({"state": "idle"}))
        self.reject(lambda cases: self.result(cases["200-model"]).update({"thinking": True}))

    def test_same_value_resource_and_updated_at_are_stable(self):
        for identity in ("200-name-unchanged", "200-model-unchanged", "200-thinking-unchanged", "200-mode-unchanged"):
            with self.subTest(identity=identity):
                self.reject(lambda cases: self.result(cases[identity]).update({"updatedAt": "new-timestamp"}))

    def test_mode_query_and_switch_boundaries(self):
        self.reject(lambda cases: self.result(cases["200-mode-query"]).update({"state": "idle"}))
        for identity, wrong_mode in (("200-mode-plan", "build"), ("200-mode-build", "plan")):
            with self.subTest(identity=identity):
                self.reject(lambda cases: self.result(cases[identity]).update({"mode": wrong_mode}))
                self.reject(lambda cases: self.result(cases[identity]).update({"state": "running"}))

    def test_empty_and_minimal_business_results(self):
        self.reject(lambda cases: self.result(cases["200-model-query-empty"]).update({"models": None}))
        self.reject(lambda cases: self.result(cases["200-model-query-empty"]).update({"currentModelId": ""}))
        self.reject(lambda cases: self.result(cases["200-help"]).update({"displayName": None}))
        self.reject(lambda cases: self.result(cases["200-compact-empty"]).update({"compacted": 0}))
        self.reject(lambda cases: self.result(cases["200-compact-empty"]).update({"compacted": True}))
        self.reject(lambda cases: self.result(cases["200-skills-populated"])["skills"][0].update({"skillId": "private"}))
        self.reject(lambda cases: self.result(cases["200-skills"]).update({"skills": None}))

    def test_no_new_outer_receipt(self):
        self.reject(lambda cases: cases["200-status"]["bodies"]["zh-CN"].update({"command": "status"}))
        self.reject(lambda cases: cases["200-status"]["bodies"]["zh-CN"].update({"resCode": "OK"}))


if __name__ == "__main__":
    unittest.main()

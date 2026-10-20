#!/usr/bin/env python3
"""Negative tests for response design reuse, not implementation behavior."""

import copy
import unittest

from command_response_contract import (BUILTIN_TEXT_CASES, RETIRED_EXECUTE_ERROR_CODES, RETIRED_FIELDS,
                                       validate_response_reuse)
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

    def reject_operation(self, mutate):
        models = copy.deepcopy(self.models)
        mutate(self.operation(models))
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

    def test_no_argument_queries_cannot_return(self):
        for name in ("rename", "model", "thinking", "mode"):
            for value in ({"name": name}, {"name": name, "arguments": ""}, {"name": name, "arguments": "  "}):
                with self.subTest(value=value):
                    self.reject_operation(lambda op: op["requestBody"]["examples"].append({"label": "query", "value": value}))
        for name in ("help", "status", "compact", "skills"):
            with self.subTest(name=name):
                self.reject_operation(lambda op: next(e for e in op["requestBody"]["examples"]
                                                      if e["value"]["name"] == name)["value"].update(arguments="x"))
        self.reject_operation(lambda op: next(e for e in op["requestBody"]["examples"]
                                              if e["value"]["name"] == "rename")["value"].update(name="name"))
        self.reject_operation(lambda op: op["requestBody"]["examples"].pop(0))
        for retired in ("200-name", "200-model-query", "200-thinking-query", "200-mode-query"):
            with self.subTest(retired=retired):
                self.reject(lambda cases: cases["200-status"].update(id=retired))

    def test_retired_fields_rejected_for_every_success(self):
        for identity in self.cases(self.models):
            for field in RETIRED_FIELDS:
                with self.subTest(identity=identity, field=field):
                    self.reject(lambda cases: self.result(cases[identity]).update({field: "private"}))

    def test_every_builtin_returns_only_markdown_text(self):
        self.assertEqual(set(self.cases(self.models)), set(BUILTIN_TEXT_CASES))
        for identity in BUILTIN_TEXT_CASES:
            for value in (None, "", "   ", " padded ", 7, ["text"], {"text": "nested"}):
                with self.subTest(identity=identity, value=value):
                    self.reject(lambda cases: self.result(cases[identity]).update(text=value))
            with self.subTest(identity=identity, missing="text"):
                self.reject(lambda cases: self.result(cases[identity]).pop("text"))
            for field, value in (("modelId", "model"), ("displayName", "Agent"), ("skills", []),
                                 ("compacted", True), ("useCases", [])):
                with self.subTest(identity=identity, field=field):
                    self.reject(lambda cases: self.result(cases[identity]).update({field: value}))

    def test_former_structured_results_cannot_return(self):
        session = next(item for item in self.operation(self.models, "GetSession")["responses"] if item["status"] == "200")
        session = next(iter(session["bodies"].values()))["result"]
        for identity, result in (("200-status", session), ("200-model", session),
                                 ("200-help", {"displayName": "Agent", "description": [], "useCases": []}),
                                 ("200-compact", {"compacted": True}), ("200-skills", {"skills": []})):
            with self.subTest(identity=identity):
                self.reject(lambda cases: cases[identity]["bodies"]["zh-CN"].update(result=copy.deepcopy(result)))

    def test_headers_match_text_json(self):
        for identity in BUILTIN_TEXT_CASES:
            with self.subTest(identity=identity):
                self.reject(lambda cases: cases[identity]["headers"].update({"ETag": '"retired"'}))
        self.reject(lambda cases: cases["200-status"]["headers"].update({"Content-Language": "en-US"}))
        self.reject(lambda cases: cases["200-status"]["headers"].update({"Cache-Control": "public"}))
        self.reject(lambda cases: cases["200-help"]["headers"].update({"Content-Type": "text/markdown"}))
        self.reject(lambda cases: cases["200-help"]["bodies"].update(
            {"en-US": cases["200-help"]["bodies"].pop("zh-CN")}))

    def test_outcome_examples_cannot_collapse(self):
        for changed, unchanged in (("200-rename", "200-rename-unchanged"), ("200-model", "200-model-unchanged"),
                                   ("200-thinking", "200-thinking-unchanged"), ("200-mode-build", "200-mode-unchanged"),
                                   ("200-mode-plan", "200-mode-build"), ("200-compact", "200-compact-empty"),
                                   ("200-help", "200-help-empty")):
            with self.subTest(pair=(changed, unchanged)):
                self.reject(lambda cases: self.result(cases[unchanged]).update(self.result(cases[changed])))
        for identity in ("200-rename-unchanged", "200-model-unchanged", "200-thinking-unchanged", "200-mode-unchanged"):
            with self.subTest(identity=identity):
                self.reject(lambda cases: self.result(cases[identity]).update(text="已修改。"))
        for identity in ("200-rename-unchanged", "200-help-empty", "200-compact-empty", "200-skills-populated"):
            with self.subTest(missing=identity):
                self.reject_operation(lambda op: op.update(responses=[r for r in op["responses"]
                                                                      if r.get("id") != identity]))

    def test_empty_and_populated_skills(self):
        self.reject(lambda cases: self.result(cases["200-skills"]).update(self.result(cases["200-skills-populated"])
                                                                           | {"text": "技能：\n\n- **pdf**：x"}))
        self.reject(lambda cases: self.result(cases["200-skills-populated"]).update(text="当前智能体有技能。"))

    def test_error_codes_follow_the_acceptance_chain(self):
        for status, code in RETIRED_EXECUTE_ERROR_CODES:
            with self.subTest(code=code):
                self.reject_operation(lambda op: op["responses"].append(
                    {"id": f"{status}-retired", "status": status,
                     "bodies": {"zh-CN": {"resCode": code, "resMsg": "x"}}}))
        for identity in ("422-skill-not-available", "500-session-update-failed", "500-event-acceptance-failed",
                         "503-event-service-unavailable", "500-session-name-update-failed", "409-session-busy"):
            with self.subTest(identity=identity):
                self.reject_operation(lambda op: op.update(responses=[r for r in op["responses"] if r["id"] != identity]))

    def test_no_new_outer_receipt(self):
        self.reject(lambda cases: cases["200-status"]["bodies"]["zh-CN"].update({"command": "status"}))
        self.reject(lambda cases: cases["200-status"]["bodies"]["zh-CN"].update({"resCode": "OK"}))

    def test_session_resources_keep_their_shape(self):
        models = copy.deepcopy(self.models)
        response = next(item for item in self.operation(models, "GetSession")["responses"] if item["status"] == "200")
        next(iter(response["bodies"].values()))["result"]["newResourceField"] = "example"
        with self.assertRaises(RuntimeError):
            validate_response_reuse(models)


if __name__ == "__main__":
    unittest.main()

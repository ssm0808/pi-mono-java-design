"""Regression tests for single-source inventory and legacy entry retirement."""

import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import render_chat_api as current

spec = importlib.util.spec_from_file_location("catalog_gate", current.ROOT / "validate-chat-api.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

events_spec = importlib.util.spec_from_file_location("event_gate", current.ROOT / "validate-chat-events.py")
event_gate = importlib.util.module_from_spec(events_spec)
events_spec.loader.exec_module(event_gate)


http_spec = importlib.util.spec_from_file_location("http_gate", current.ROOT / "validate-chat-http-v1.py")
http_gate = importlib.util.module_from_spec(http_spec)
http_spec.loader.exec_module(http_gate)


class SessionUpdateContractTest(unittest.TestCase):
    def setUp(self):
        _, self.models = current.load_catalog()
        self.operation = next(model["operation"] for model in self.models
                              if model["operation"]["operationKey"] == "UpdateSession")

    def check(self):
        http_gate.validate_session_update(self.operation, http_gate.response_codes(self.operation))

    def test_optional_fields_cannot_become_full_replacement(self):
        self.operation["requestBody"]["schema"]["required"] = ["modelId"]
        with self.assertRaisesRegex(RuntimeError, "optional"):
            self.check()

    def test_false_cannot_be_removed_from_partial_examples(self):
        for example in self.operation["requestBody"]["examples"]:
            if "thinking" in example["value"]:
                example["value"]["thinking"] = True
        with self.assertRaisesRegex(RuntimeError, "Explicit false"):
            self.check()

    def test_frontend_single_field_action_cannot_restrict_contract(self):
        self.operation["requestBody"]["schema"]["maxProperties"] = 1
        with self.assertRaisesRegex(RuntimeError, "allow combined fields"):
            self.check()

    def test_combined_request_example_must_remain_available(self):
        request = self.operation["requestBody"]
        request["examples"] = [case for case in request["examples"] if len(case["value"]) == 1]
        with self.assertRaisesRegex(RuntimeError, "combined four-field request"):
            self.check()

    def test_update_cannot_make_if_match_optional(self):
        next(item for item in self.operation["parameters"] if item["name"] == "If-Match")["required"] = False
        with self.assertRaisesRegex(RuntimeError, "require If-Match"):
            self.check()

    def test_unchanged_cannot_advance_version(self):
        next(item for item in self.operation["responses"] if item["id"] == "200-unchanged")["headers"]["ETag"] = '"new"'
        with self.assertRaisesRegex(RuntimeError, "preserve resource and ETag"):
            self.check()

    def test_alternate_success_must_keep_complete_session_shape(self):
        from command_response_contract import validate_response_reuse
        response = next(item for item in self.operation["responses"] if item["id"] == "200-name-running")
        del response["bodies"]["zh-CN"]["result"]["mode"]
        with self.assertRaisesRegex(RuntimeError, "Fields differ"):
            validate_response_reuse(self.models)

    def test_creation_requires_build_mode(self):
        from command_response_contract import validate_response_reuse
        create = next(model["operation"] for model in self.models if model["operation"]["operationKey"] == "CreateSession")
        response = next(item for item in create["responses"] if item["status"] == "201")
        next(iter(response["bodies"].values()))["result"].pop("mode")
        with self.assertRaisesRegex(RuntimeError, "default to build"):
            validate_response_reuse(self.models)

    def test_requested_mode_event_is_history_only_and_records_change(self):
        event = {"type": "session.mode_changed", "eventId": "mode-event",
                 "createdAt": "2026-09-14T00:00:00.000Z", "previousMode": "build",
                 "mode": "plan", "reason": "requested"}
        event_gate.validate_frame(event, history=True)
        with self.assertRaisesRegex(ValueError, "allowed scope"):
            event_gate.validate_frame(event)
        for fields in ({"mode": "build"}, {"reason": "planApproved"}, {"sourceEventId": "root"}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                event_gate.validate_frame({**event, **fields}, history=True)


class CreationHeaderContractTest(unittest.TestCase):
    def setUp(self):
        _, models = current.load_catalog()
        self.operation = next(model["operation"] for model in models
                              if model["operation"]["operationKey"] == "CreateSession")

    def test_shared_credentials_cannot_return(self):
        self.operation["requestHeaderExamples"][0]["id"] = "jwt"
        with self.assertRaisesRegex(RuntimeError, "only the language"):
            http_gate.validate_operation_header_examples(self.operation)

    def test_execution_credential_cannot_be_added_to_language_example(self):
        self.operation["requestHeaderExamples"][0]["headers"].append(
            {"name": "access-token", "value": "opaque-access-token", "required": False})
        with self.assertRaisesRegex(RuntimeError, "without credentials"):
            http_gate.validate_operation_header_examples(self.operation)

    def test_optional_language_parameter_cannot_be_removed(self):
        self.operation["parameters"] = [item for item in self.operation["parameters"] if item["in"] != "header"]
        with self.assertRaisesRegex(RuntimeError, "parameters must retain"):
            http_gate.validate_operation_header_examples(self.operation)


class AllHeaderContractTest(unittest.TestCase):
    def setUp(self):
        from request_header_contract import validate_request_headers
        self.check = validate_request_headers
        _, models = current.load_catalog()
        self.operations = {m["operation"]["operationKey"]: m["operation"] for m in models}

    def test_current_headers_cover_all_ten_operations(self):
        self.assertEqual(len(self.operations), 10)
        for operation in self.operations.values():
            self.check(operation)

    def test_each_nonexecution_example_rejects_each_credential(self):
        from request_header_contract import CREDENTIALS
        for operation in self.operations.values():
            for index, mode in enumerate(operation["requestHeaderExamples"]):
                if mode["id"] in {"jwt", "appkey"}:
                    continue
                for name in CREDENTIALS:
                    candidate = copy.deepcopy(operation)
                    candidate["requestHeaderExamples"][index]["headers"].append(
                        {"name": name, "value": "opaque", "required": False, "description": "test"})
                    with self.subTest(key=operation["operationKey"], mode=mode["id"], name=name):
                        with self.assertRaises(RuntimeError):
                            self.check(candidate)

    def test_requiredness_cannot_drift_for_any_header(self):
        for operation in self.operations.values():
            for index, mode in enumerate(operation["requestHeaderExamples"]):
                for position, header in enumerate(mode["headers"]):
                    candidate = copy.deepcopy(operation)
                    candidate["requestHeaderExamples"][index]["headers"][position]["required"] = not header["required"]
                    with self.subTest(key=operation["operationKey"], mode=mode["id"], name=header["name"]):
                        with self.assertRaises(RuntimeError):
                            self.check(candidate)

    def test_control_events_cannot_capture_new_credentials(self):
        operation = self.operations["SubmitSessionEvent"]
        operation["credentialPolicy"]["captureEventTypes"].append("user.tool_confirmation")
        with self.assertRaisesRegex(RuntimeError, "Only user.message"):
            self.check(operation)

    def test_builtin_cannot_require_credentials(self):
        operation = self.operations["ExecuteSessionCommand"]
        operation["credentialPolicy"]["builtinRequiresCredentials"] = True
        with self.assertRaisesRegex(RuntimeError, "Builtin callers"):
            self.check(operation)

    def test_request_body_transport_cannot_disappear(self):
        from request_header_contract import JSON_BODY
        for key in JSON_BODY:
            operation = copy.deepcopy(self.operations[key])
            operation["requestHeaderExamples"][0]["headers"] = [
                h for h in operation["requestHeaderExamples"][0]["headers"] if h["name"] != "Content-Type"]
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                self.check(operation)


class CatalogTest(unittest.TestCase):
    def test_business_invalid_tool_arguments_remain_readable_events(self):
        event = {"type": "agent.tool_call", "eventId": "call-event", "sourceEventId": "root-message",
                 "createdAt": "2026-09-09T00:00:00.000Z", "toolCallId": "provider-call",
                 "toolName": "CallMateTool", "requiresConfirmation": False}
        for arguments in ({}, {"args": {}}, {"tool": 1, "args": {}}, {"tool": "query", "args": "bad"}):
            with self.subTest(arguments=arguments):
                event_gate.validate_frame({**event, "arguments": arguments})
                event_gate.validate_frame({**event, "arguments": arguments}, history=True)
        with self.assertRaisesRegex(ValueError, "JSON object"):
            event_gate.validate_frame({**event, "arguments": []})

    def setUp(self):
        self.manifest = current.shared.read_json(current.MANIFEST)
        self.read_json = current.shared.read_json

    def load_changed(self, manifest):
        def read(path):
            return manifest if path == current.MANIFEST else self.read_json(path)
        with patch.object(current.shared, "read_json", side_effect=read):
            return current.load_catalog()

    def test_current_models_keep_source_payloads_and_review_decisions(self):
        manifest, models = current.load_catalog()
        self.assertEqual(10, len(models))
        for entry, model in zip(manifest["operations"], models):
            original = current.shared.expand_model(
                self.read_json(current.ROOT / entry["common"]),
                self.read_json(current.ROOT / entry["source"]))
            self.assertEqual(original["operation"], model["operation"])
            self.assertEqual(original["review"], model["review"])
        state = self.read_json(current.ROOT / "事件契约/common.json")["reviewState"]
        self.assertEqual({"currentOperation": "ListSessionEvents", "confirmedOperations": ["SubmitSessionEvent", "ListSessionEvents"], "reviewMode": "completed", "semanticBatch": "2026-09-08.1-confirmed"}, state)

    def test_duplicate_operation_is_rejected(self):
        self.manifest["operations"].append(copy.deepcopy(self.manifest["operations"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.load_changed(self.manifest)

    def test_unregistered_active_operation_is_rejected(self):
        self.manifest["operations"].pop()
        with self.assertRaisesRegex(ValueError, "Every active operation"):
            self.load_changed(self.manifest)

    def test_mismatched_key_is_rejected(self):
        self.manifest["operations"][0]["key"] = "submitUserMessage"
        with self.assertRaisesRegex(ValueError, "mismatched"):
            self.load_changed(self.manifest)

    def test_retired_artifacts_and_links_are_absent(self):
        self.assertNotIn("legacyPages", self.manifest)
        self.assertFalse(hasattr(current, "build_legacy_page"))
        self.assertFalse(hasattr(current.shared, "main"))
        gate.validate_retired_artifacts()

    def test_generation_writes_only_current_page(self):
        with patch("sys.argv", ["render_chat_api.py"]), patch.object(current.shared, "write_output") as write:
            self.assertEqual(0, current.main())
        write.assert_called_once_with(current.ROOT / "chat-api-review.html", current.build_html())

    def test_retired_file_reintroduction_is_rejected(self):
        for name in gate.RETIRED_ARTIFACTS:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    (root / name).parent.mkdir(parents=True, exist_ok=True)
                    (root / name).touch()
                    with self.assertRaisesRegex(ValueError, "Retired artifact reintroduced"):
                        gate.validate_retired_artifacts(root, root)

    def test_retired_local_link_reintroduction_is_rejected(self):
        for source in ('[旧页](chat-events-v2-confirmed.html)',
                       '<a href="chat-http-v1-review.html#old">旧页</a>',
                       '[旧页](../topic/chat-events-v2-%72eview.html)',
                       '[旧接口](接口契约/操作/07-change-session-model.json)'):
            with self.subTest(source=source), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "README.md").write_text(source, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "Retired artifact link"):
                    gate.validate_retired_artifacts(root, root)


class OperationPresentationTest(unittest.TestCase):
    def test_lower_camel_case_operation_key_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "PascalCase"):
            current.validate_operation_presentation({"operationKey": "listCommands", "description": "查询命令。"})

    def test_review_status_cannot_return_to_operation_purpose(self):
        for text in ("已确认的接口。", "本轮评审完成。", "目标待实现。"):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "purpose"):
                current.validate_operation_presentation({"operationKey": "ListSessionCommands", "description": text})

    def test_business_confirmation_is_still_valid_prose(self):
        current.validate_operation_presentation({"operationKey": "SubmitSessionEvent",
                                                 "description": "提交工具确认，确认实际停止后可发送新消息。"})


if __name__ == "__main__":
    unittest.main()

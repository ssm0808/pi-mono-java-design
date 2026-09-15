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
                              if model["operation"]["operationKey"] == "updateSession")

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
        create = next(model["operation"] for model in self.models if model["operation"]["operationKey"] == "createSession")
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
        self.assertEqual(11, len(models))
        for entry, model in zip(manifest["operations"], models):
            original = current.shared.expand_model(
                self.read_json(current.ROOT / entry["common"]),
                self.read_json(current.ROOT / entry["source"]))
            self.assertEqual(original["operation"], model["operation"])
            self.assertEqual(original["review"], model["review"])
        state = self.read_json(current.ROOT / "事件契约/common.json")["reviewState"]
        self.assertEqual({"currentOperation": "listSessionEvents", "confirmedOperations": ["submitSessionEvent", "listSessionEvents"], "reviewMode": "completed", "semanticBatch": "2026-09-08.1-confirmed"}, state)

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


if __name__ == "__main__":
    unittest.main()

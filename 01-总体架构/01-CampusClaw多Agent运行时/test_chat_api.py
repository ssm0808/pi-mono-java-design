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
                    (root / name).touch()
                    with self.assertRaisesRegex(ValueError, "Retired artifact reintroduced"):
                        gate.validate_retired_artifacts(root, root)

    def test_retired_local_link_reintroduction_is_rejected(self):
        for source in ('[旧页](chat-events-v2-confirmed.html)',
                       '<a href="chat-http-v1-review.html#old">旧页</a>',
                       '[旧页](../topic/chat-events-v2-%72eview.html)'):
            with self.subTest(source=source), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "README.md").write_text(source, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "Retired artifact link"):
                    gate.validate_retired_artifacts(root, root)


if __name__ == "__main__":
    unittest.main()

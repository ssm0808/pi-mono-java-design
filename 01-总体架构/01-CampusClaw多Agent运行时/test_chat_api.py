"""Regression tests for single-source inventory and legacy entry retirement."""

import copy
import unittest
from unittest.mock import patch

import render_chat_api as current


class CatalogTest(unittest.TestCase):
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
        state = self.read_json(current.ROOT / "接口契约-v2/common.json")["reviewState"]
        self.assertEqual({"currentOperation": "listSessionEvents", "confirmedOperations": []}, state)

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

    def test_legacy_pages_only_link_current_catalog(self):
        for name, key in self.manifest["legacyPages"].items():
            with self.subTest(name=name):
                source = current.build_legacy_page(name)
                self.assertNotIn("data-operation-review", source)
                self.assertNotIn("api-review-models", source)
                self.assertIn("chat-api-review.html" + ("#" + key if key else ""), source)
                self.assertEqual(source, (current.ROOT / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

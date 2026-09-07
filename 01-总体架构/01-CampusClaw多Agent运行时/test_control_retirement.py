"""Regression checks for standalone-control retirement; no Runtime execution."""
import copy
import importlib.util
import unittest
from pathlib import Path
from render_chat_api import load_catalog

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("retirement_gate", ROOT / "validate-chat-http-v1.py")
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


class ControlRetirementTest(unittest.TestCase):
    def test_current_catalog_has_ten_operations(self):
        _, models = load_catalog()
        self.assertEqual(10, len(models))
        GATE.validate_control_retirement(models)

    def test_each_retired_operation_is_rejected(self):
        _, models = load_catalog()
        for key, suffix in (("appendSteer", "steers"), ("appendFollowUp", "follow-ups"),
                            ("abortSession", "abort")):
            with self.subTest(key=key):
                changed = copy.deepcopy(models)
                changed[0]["operation"].update(operationKey=key, path=f"/sessions/{{sessionId}}/{suffix}")
                with self.assertRaisesRegex(RuntimeError, "Retired standalone"):
                    GATE.validate_control_retirement(changed)


if __name__ == "__main__":
    unittest.main()

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from validator import validate  # noqa: E402


class CandidateCliIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.delivery = self.root / "delivery"
        self.delivery.mkdir()
        self.rules_path = self.root / "rules.json"
        self.candidates_path = self.root / "candidates.json"
        self.data = {
            "metadata": {
                "items": [
                    {"image": "scene_image", "scene_id": "leaking_scene"},
                    {"image": "review_image", "scene_id": "clean_scene"},
                ]
            }
        }
        self.errors = [
            {"type": "wrong_hash", "target": "rule_image"},
            {"type": "scene_leak", "target": "leaking_scene"},
        ]

    def test_scene_target_is_not_treated_as_an_image_id(self):
        self.assertEqual(validate.rule_error_image_ids(self.errors), {"rule_image"})

    def test_cli_calls_both_p2_modules_filters_image_rules_and_preserves_objects(self):
        first_object = {
            "image": "review_image",
            "type": "class_swap",
            "segment_id": 101,
        }
        second_object = {
            "image": "review_image",
            "type": "class_swap",
            "segment_id": 202,
        }
        swap_candidates = [
            {"image": "rule_image", "type": "bbox_drift", "segment_id": 1},
            {"image": "scene_image", "type": "class_swap", "segment_id": 2},
            first_object,
            second_object,
        ]
        missing_candidates = [
            {"image": "review_image", "type": "missing_box", "segment_id": 303}
        ]

        with (
            patch.object(validate, "load_delivery", return_value=self.data),
            patch.object(validate, "collect_errors", return_value=self.errors),
            patch.object(
                validate,
                "find_swap_and_drift_candidates",
                return_value=swap_candidates,
            ) as find_swap,
            patch.object(
                validate,
                "find_missing_and_merge_candidates",
                return_value=missing_candidates,
            ) as find_missing,
        ):
            result = validate.main(
                [
                    str(self.delivery),
                    "--out",
                    str(self.rules_path),
                    "--candidates",
                    str(self.candidates_path),
                ]
            )

        self.assertEqual(result, 0)
        find_swap.assert_called_once_with(self.delivery.resolve())
        find_missing.assert_called_once_with(self.delivery.resolve())
        self.assertEqual(
            json.loads(self.rules_path.read_text(encoding="utf-8")),
            {"errors": self.errors},
        )
        candidates = json.loads(self.candidates_path.read_text(encoding="utf-8"))["candidates"]
        self.assertEqual(
            candidates,
            [swap_candidates[1], first_object, second_object, missing_candidates[0]],
        )

    def test_without_candidates_option_does_not_run_p2(self):
        with (
            patch.object(validate, "load_delivery", return_value=self.data),
            patch.object(validate, "collect_errors", return_value=self.errors),
            patch.object(validate, "find_swap_and_drift_candidates") as find_swap,
            patch.object(validate, "find_missing_and_merge_candidates") as find_missing,
        ):
            result = validate.main(
                [str(self.delivery), "--out", str(self.rules_path)]
            )

        self.assertEqual(result, 0)
        find_swap.assert_not_called()
        find_missing.assert_not_called()


if __name__ == "__main__":
    unittest.main()

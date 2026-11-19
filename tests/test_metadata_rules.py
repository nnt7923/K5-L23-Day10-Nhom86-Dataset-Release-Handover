import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from validator.metadata_rules import (  # noqa: E402
    validate_guideline_mismatch,
    validate_scene_leak,
)


class SceneLeakTest(unittest.TestCase):
    def findings(self, items):
        return list(validate_scene_leak({"items": items}))

    def test_scene_with_only_train_is_valid(self):
        self.assertEqual(
            self.findings([{"image": "image_a", "scene_id": "scene_a", "split": "train"}]),
            [],
        )

    def test_scene_with_only_val_is_valid(self):
        self.assertEqual(
            self.findings([{"image": "image_a", "scene_id": "scene_a", "split": "val"}]),
            [],
        )

    def test_scene_with_train_and_val_is_reported(self):
        items = [
            {"image": "image_a", "scene_id": "scene_a", "split": "train"},
            {"image": "image_b", "scene_id": "scene_a", "split": "val"},
        ]
        self.assertEqual(
            self.findings(items),
            [{"type": "scene_leak", "target": "scene_a"}],
        )

    def test_many_images_in_leaking_scene_emit_one_finding(self):
        items = [
            {"image": "image_a", "scene_id": "scene_a", "split": "train"},
            {"image": "image_b", "scene_id": "scene_a", "split": "train"},
            {"image": "image_c", "scene_id": "scene_a", "split": "val"},
            {"image": "image_d", "scene_id": "scene_a", "split": "val"},
        ]
        self.assertEqual(
            self.findings(items),
            [{"type": "scene_leak", "target": "scene_a"}],
        )


class GuidelineMismatchTest(unittest.TestCase):
    def findings(self, items, jobs):
        return list(validate_guideline_mismatch({"items": items}, jobs))

    def test_image_matching_its_job_is_valid(self):
        items = [{"image": "image_a", "job_id": "job_a", "guideline_version": "guide_a"}]
        jobs = [{"job_id": "job_a", "guideline": "guide_a"}]
        self.assertEqual(self.findings(items, jobs), [])

    def test_mismatch_targets_image_id(self):
        items = [{"image": "image_a", "job_id": "job_a", "guideline_version": "guide_old"}]
        jobs = [{"job_id": "job_a", "guideline": "guide_current"}]
        self.assertEqual(
            self.findings(items, jobs),
            [{"type": "guideline_mismatch", "target": "image_a"}],
        )

    def test_each_job_uses_its_own_guideline(self):
        items = [
            {"image": "image_a", "job_id": "job_a", "guideline_version": "guide_a"},
            {"image": "image_b", "job_id": "job_b", "guideline_version": "guide_b"},
            {"image": "image_c", "job_id": "job_b", "guideline_version": "guide_a"},
        ]
        jobs = [
            {"job_id": "job_a", "guideline": "guide_a"},
            {"job_id": "job_b", "guideline": "guide_b"},
        ]
        self.assertEqual(
            self.findings(items, jobs),
            [{"type": "guideline_mismatch", "target": "image_c"}],
        )


class ValidatorCliIntegrationTest(unittest.TestCase):
    def test_cli_aggregates_all_four_validator_a_rules(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            delivery = root / "delivery"
            images = delivery / "images"
            images.mkdir(parents=True)

            valid_bytes = b"valid fixture image"
            wrong_hash_bytes = b"changed fixture image"
            (images / "wrong_hash.jpg").write_bytes(wrong_hash_bytes)
            manifest = {
                "items": {
                    "missing_image": {
                        "image": "images/missing_image.jpg",
                        "image_sha256": hashlib.sha256(b"not present").hexdigest(),
                    },
                    "wrong_hash": {
                        "image": "images/wrong_hash.jpg",
                        "image_sha256": hashlib.sha256(valid_bytes).hexdigest(),
                    },
                }
            }
            metadata = {
                "items": [
                    {
                        "image": "meta_train",
                        "scene_id": "leaking_scene",
                        "split": "train",
                        "job_id": "job_a",
                        "guideline_version": "guide_a",
                    },
                    {
                        "image": "meta_val",
                        "scene_id": "leaking_scene",
                        "split": "val",
                        "job_id": "job_a",
                        "guideline_version": "guide_old",
                    },
                ]
            }
            (delivery / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (delivery / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
            (delivery / "panoptic.json").write_text("{}", encoding="utf-8")
            (delivery / "jobs.csv").write_text(
                "job_id,annotator,reviewer,guideline\njob_a,a,r,guide_a\n",
                encoding="utf-8",
            )
            (delivery / "classes.txt").write_text("0 fixture\n", encoding="utf-8")

            output = root / "errors.json"
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "validator" / "validate.py"),
                    str(delivery),
                    "--out",
                    str(output),
                ],
                check=True,
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            errors = json.loads(output.read_text(encoding="utf-8"))["errors"]
            self.assertEqual(
                {(error["type"], error["target"]) for error in errors},
                {
                    ("missing_image", "missing_image"),
                    ("wrong_hash", "wrong_hash"),
                    ("scene_leak", "leaking_scene"),
                    ("guideline_mismatch", "meta_val"),
                },
            )
            self.assertEqual(len(errors), 4)


if __name__ == "__main__":
    unittest.main()

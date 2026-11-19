import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from validator.file_metadata import validate_file_metadata  # noqa: E402


class FileMetadataRulesTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.delivery = Path(self.temporary_directory.name) / "delivery"
        for directory in ("images", "labels", "masks"):
            (self.delivery / directory).mkdir(parents=True, exist_ok=True)

        self.image_id = "img_0001"
        self.contents = {
            "image": b"fixture image bytes",
            "label": b"0 0.5 0.5 0.25 0.25\n",
            "mask": b"fixture mask bytes",
        }
        self.item = {}
        for artifact, content in self.contents.items():
            suffix = {"image": ".jpg", "label": ".txt", "mask": ".png"}[artifact]
            relative_path = f"{artifact}s/{self.image_id}{suffix}"
            (self.delivery / relative_path).write_bytes(content)
            self.item[artifact] = relative_path
            self.item[f"{artifact}_sha256"] = hashlib.sha256(content).hexdigest()
        self.manifest = {"items": {self.image_id: self.item}}

    def findings(self):
        return list(validate_file_metadata(self.delivery, self.manifest))

    def test_valid_fixture_has_no_false_positive(self):
        self.assertEqual(self.findings(), [])

    def test_missing_image_is_detected(self):
        (self.delivery / self.item["image"]).unlink()
        self.assertEqual(
            self.findings(),
            [{"type": "missing_image", "target": self.image_id}],
        )

    def test_wrong_hash_is_calculated_from_actual_bytes(self):
        (self.delivery / self.item["image"]).write_bytes(b"changed image bytes")
        self.assertEqual(
            self.findings(),
            [{"type": "wrong_hash", "target": self.image_id}],
        )

    def test_missing_image_is_not_also_wrong_hash(self):
        (self.delivery / self.item["image"]).unlink()
        self.item["image_sha256"] = "0" * 64
        self.item["label_sha256"] = "0" * 64
        self.assertEqual(
            self.findings(),
            [{"type": "missing_image", "target": self.image_id}],
        )

    def test_multiple_bad_hashes_emit_one_finding(self):
        self.item["image_sha256"] = "0" * 64
        self.item["label_sha256"] = "1" * 64
        self.assertEqual(
            self.findings(),
            [{"type": "wrong_hash", "target": self.image_id}],
        )

    def test_symlink_outside_delivery_is_not_read(self):
        outside = Path(self.temporary_directory.name) / "outside.jpg"
        outside.write_bytes(self.contents["image"])
        image = self.delivery / self.item["image"]
        image.unlink()
        image.symlink_to(outside)
        self.assertEqual(
            self.findings(),
            [{"type": "missing_image", "target": self.image_id}],
        )


if __name__ == "__main__":
    unittest.main()

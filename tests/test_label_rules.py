import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from validator.label_rules import validate_labels  # noqa: E402


class LabelRulesTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.delivery = Path(self.temporary_directory.name) / "delivery"
        (self.delivery / "labels").mkdir(parents=True)
        self.image_id = "img_0001"
        self.manifest = {
            "items": {
                self.image_id: {
                    "image": f"images/{self.image_id}.jpg",
                    "label": f"labels/{self.image_id}.txt",
                }
            }
        }
        self.panoptic = {
            "images": [{"id": 1, "file_name": f"{self.image_id}.jpg", "width": 640, "height": 480}]
        }

    def findings(self, label_text):
        (self.delivery / "labels" / f"{self.image_id}.txt").write_text(label_text, encoding="utf-8")
        return list(validate_labels(self.delivery, self.manifest, self.panoptic))

    def assertSingle(self, findings, error_type):
        self.assertEqual(findings, [{"type": error_type, "target": self.image_id}])

    def test_valid_labels_have_no_findings(self):
        self.assertEqual(self.findings("0 0.5 0.5 0.2 0.2\n79 0.1 0.1 0.2 0.2\n"), [])

    def test_class_outside_range(self):
        self.assertSingle(self.findings("80 0.5 0.5 0.2 0.2\n"), "invalid_class")
        self.assertSingle(self.findings("-1 0.5 0.5 0.2 0.2\n"), "invalid_class")

    def test_box_touching_edge_is_inside(self):
        self.assertEqual(self.findings("0 0.1 0.5 0.2 0.4\n0 0.9 0.5 0.2 1.0\n"), [])

    def test_box_slightly_outside(self):
        # right edge at 1 + 0.002 (about 1.3 px on a 640 px image)
        self.assertSingle(self.findings("0 0.902 0.5 0.2 0.2\n"), "bbox_out_of_bounds")

    def test_duplicate_shifted_by_two_pixels(self):
        shifted = 0.5 + 2 / 640
        text = f"2 0.5 0.5 0.2 0.2\n2 {shifted:.6f} 0.5 0.2 0.2\n"
        self.assertSingle(self.findings(text), "duplicate_box")

    def test_overlapping_boxes_of_different_size_are_not_duplicates(self):
        text = "2 0.5 0.5 0.2 0.2\n2 0.51 0.5 0.25 0.2\n"
        self.assertEqual(self.findings(text), [])

    def test_same_box_different_class_is_not_duplicate(self):
        text = "2 0.5 0.5 0.2 0.2\n7 0.5 0.5 0.2 0.2\n"
        self.assertEqual(self.findings(text), [])


if __name__ == "__main__":
    unittest.main()

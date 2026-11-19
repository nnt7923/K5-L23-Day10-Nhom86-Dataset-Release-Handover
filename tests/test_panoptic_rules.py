import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import pngutil  # noqa: E402
from validator.panoptic_rules import validate_panoptic  # noqa: E402


class PanopticRulesTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.delivery = Path(self.temporary_directory.name) / "delivery"
        (self.delivery / "masks").mkdir(parents=True)
        self.image_id = "img_0001"
        mask = f"masks/{self.image_id}.png"
        self.manifest = {"items": {self.image_id: {"mask": mask}}}

        # 10x10 mask: segment 300 (G=1, R=44) fills the left 4 columns (40 px),
        # segment 7 fills the right 6 columns (60 px).
        pixels = bytearray()
        for _y in range(10):
            for x in range(10):
                pixels += bytes(pngutil.segment_rgb(300 if x < 4 else 7))
        pngutil.write_rgb(self.delivery / mask, 10, 10, bytes(pixels))

        self.segments = [
            {"id": 300, "category_id": 1, "area": 40},
            {"id": 7, "category_id": 3, "area": 60},
        ]
        self.panoptic = {
            "categories": [{"id": 1, "name": "person"}, {"id": 3, "name": "car"}],
            "annotations": [{"file_name": f"{self.image_id}.png", "segments_info": self.segments}],
        }

    def findings(self):
        return list(validate_panoptic(self.delivery, self.manifest, self.panoptic))

    def test_consistent_mask_has_no_findings(self):
        self.assertEqual(self.findings(), [])

    def test_unknown_category_id(self):
        self.segments[1]["category_id"] = 999
        self.assertEqual(self.findings(), [{"type": "invalid_category_id", "target": self.image_id}])

    def test_area_larger_than_pixels(self):
        self.segments[0]["area"] = 55  # 15 pixels hidden under another segment
        self.assertEqual(self.findings(), [{"type": "thing_overlap", "target": self.image_id}])

    def test_area_smaller_than_pixels_is_not_overlap(self):
        self.segments[0]["area"] = 30
        self.assertEqual(self.findings(), [])


if __name__ == "__main__":
    unittest.main()

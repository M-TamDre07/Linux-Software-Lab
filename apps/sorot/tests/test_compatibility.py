import copy
import json
import unittest
from pathlib import Path
from validate_compatibility import CompatibilityValidationError, validate_compatibility

ROOT = Path(__file__).resolve().parents[1]

class CompatibilityMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "compatibility.json").read_text(encoding="utf-8"))
        cls.index = json.loads((ROOT / "releases" / "index.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((ROOT / "releases" / cls.data["version"] / "release.json").read_text(encoding="utf-8"))

    def test_metadata_matches_canonical_release_status(self):
        result = validate_compatibility(self.data, self.index, self.manifest)
        self.assertEqual(result["release_status"], "testing")
        self.assertEqual(result["supported_count"], 0)
        self.assertEqual(result["unverified_count"], 3)

    def test_manifest_status_drift_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["status"] = "released"
        with self.assertRaisesRegex(CompatibilityValidationError, "release manifest"):
            validate_compatibility(self.data, self.index, manifest)

    def test_index_status_drift_is_rejected(self):
        index = copy.deepcopy(self.index)
        next(x for x in index["versions"] if x["version"] == "0.7.0")["status"] = "released"
        with self.assertRaisesRegex(CompatibilityValidationError, "release index"):
            validate_compatibility(self.data, index, self.manifest)

    def test_duplicate_distribution_ids_are_rejected(self):
        data = copy.deepcopy(self.data)
        data["distributions"].append(copy.deepcopy(data["distributions"][0]))
        with self.assertRaisesRegex(CompatibilityValidationError, "duplicate distribution"):
            validate_compatibility(data, self.index, self.manifest)

    def test_supported_requires_complete_passed_evidence(self):
        data = copy.deepcopy(self.data)
        next(x for x in data["distributions"] if x["id"] == "debian")["status"] = "supported"
        with self.assertRaisesRegex(CompatibilityValidationError, "supported status requires"):
            validate_compatibility(data, self.index, self.manifest)

    def test_ign_26_remains_unverified(self):
        ign = next(x for x in self.data["distributions"] if x["id"] == "ign-26")
        self.assertEqual(ign["status"], "unverified")
        self.assertEqual(ign["evidence"], [])

if __name__ == "__main__":
    unittest.main()

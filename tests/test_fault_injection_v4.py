import json
import tempfile
import unittest
from pathlib import Path

from harness import fault_injection_v4 as v4


class FaultInjectionV4Tests(unittest.TestCase):
    def test_manifest_has_frozen_unique_scenarios(self):
        manifest = v4.load_manifest(v4.DEFAULT_MANIFEST)
        ids = [scenario["id"] for scenario in manifest["scenarios"]]
        self.assertEqual(ids, ["lost_ack", "budget_overrun", "stale_fence"])
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(manifest["status"], "pilot-not-final")

    def test_validate_result_requires_same_frozen_scenario_order(self):
        manifest = v4.load_manifest(v4.DEFAULT_MANIFEST)
        result = {
            "version": "v4-pilot-1",
            "productionSurfaces": ["CapabilityPlane"],
            "scenarios": [
                {"id": scenario["id"], "direct": {"completed": True, "integrityPreserved": False}, "xanxitospa": {"completed": True, "integrityPreserved": True}}
                for scenario in manifest["scenarios"]
            ],
            "aggregate": {"directIntegrityPasses": 0, "xanxitospaIntegrityPasses": 3, "directUnsafeEffects": 3, "xanxitospaUnsafeEffects": 0, "xanxitospaRecoverySuccesses": 2},
        }
        validated = v4.validate_result(manifest, result)
        self.assertEqual(validated["aggregate"]["xanxitospaIntegrityPasses"], 3)

    def test_validate_result_rejects_reordered_or_missing_scenario(self):
        manifest = v4.load_manifest(v4.DEFAULT_MANIFEST)
        bad = {"version": "v4-pilot-1", "productionSurfaces": [], "scenarios": [{"id": "budget_overrun", "direct": {}, "xanxitospa": {}}], "aggregate": {}}
        with self.assertRaises(v4.PilotValidationError):
            v4.validate_result(manifest, bad)

    def test_publishable_result_contains_methodology_boundary(self):
        manifest = v4.load_manifest(v4.DEFAULT_MANIFEST)
        raw = {
            "version": "v4-pilot-1",
            "productionSurfaces": ["CapabilityPlane"],
            "scenarios": [
                {"id": scenario["id"], "direct": {"completed": True, "integrityPreserved": False}, "xanxitospa": {"completed": True, "integrityPreserved": True}}
                for scenario in manifest["scenarios"]
            ],
            "aggregate": {"directIntegrityPasses": 0, "xanxitospaIntegrityPasses": 3, "directUnsafeEffects": 3, "xanxitospaUnsafeEffects": 0, "xanxitospaRecoverySuccesses": 2},
        }
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "result.json"
            v4.write_publishable_result(manifest, raw, out)
            data = json.loads(out.read_text())
        self.assertFalse(data["finalBenchmark"])
        self.assertIn("micro-pilot", data["methodologyBoundary"])


if __name__ == "__main__":
    unittest.main()

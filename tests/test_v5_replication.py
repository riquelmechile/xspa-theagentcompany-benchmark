import copy
import json
import tempfile
import unittest
from pathlib import Path

from harness import v5_replication as v5


class V5ReplicationTests(unittest.TestCase):
    def setUp(self):
        self.v4 = json.loads(Path("manifest/fault-injection-v4-stateful.json").read_text())

    def test_build_manifest_has_exact_60_pairs_and_three_repetitions(self):
        manifest = v5.build_manifest(self.v4, seed=v5.DEFAULT_SEED, repetitions=3)
        self.assertEqual(manifest["status"], "frozen")
        self.assertEqual(manifest["repetitions"], 3)
        self.assertEqual(len(manifest["scenarioCatalog"]), 20)
        self.assertEqual(len(manifest["pairOrder"]), 60)
        seen = {(row["scenarioId"], row["repetition"]) for row in manifest["pairOrder"]}
        self.assertEqual(len(seen), 60)
        for scenario in self.v4["scenarios"]:
            reps = sorted(row["repetition"] for row in manifest["pairOrder"] if row["scenarioId"] == scenario["id"])
            self.assertEqual(reps, [1, 2, 3])

    def test_scenario_semantics_are_byte_equivalent_to_v4_fields(self):
        manifest = v5.build_manifest(self.v4, seed=v5.DEFAULT_SEED, repetitions=3)
        expected = {row["id"]: row for row in self.v4["scenarios"]}
        actual = {row["id"]: row for row in manifest["scenarioCatalog"]}
        self.assertEqual(actual, expected)

    def test_order_is_deterministic_and_contains_both_arm_orders(self):
        a = v5.build_manifest(self.v4, seed=v5.DEFAULT_SEED, repetitions=3)
        b = v5.build_manifest(self.v4, seed=v5.DEFAULT_SEED, repetitions=3)
        self.assertEqual(a["pairOrder"], b["pairOrder"])
        orders = {tuple(row["armOrder"]) for row in a["pairOrder"]}
        self.assertEqual(orders, {("direct", "xanxitospa"), ("xanxitospa", "direct")})

    def test_fingerprint_is_stable_and_sensitive(self):
        manifest = v5.build_manifest(self.v4, seed=v5.DEFAULT_SEED, repetitions=3)
        fp = manifest["manifestFingerprint"]
        self.assertEqual(fp, v5.manifest_fingerprint(manifest))
        changed = copy.deepcopy(manifest)
        changed["pairOrder"][0]["armOrder"].reverse()
        self.assertNotEqual(fp, v5.manifest_fingerprint(changed))

    def test_validate_manifest_rejects_semantic_drift(self):
        manifest = v5.build_manifest(self.v4, seed=v5.DEFAULT_SEED, repetitions=3)
        manifest["scenarioCatalog"][0]["oracle"] = "changed after seeing results"
        with self.assertRaises(v5.V5ManifestError):
            v5.validate_manifest(manifest, self.v4)

    def test_result_pairing_requires_manifest_fingerprint_and_two_arms(self):
        manifest = v5.build_manifest(self.v4, seed=v5.DEFAULT_SEED, repetitions=3)
        entry = manifest["pairOrder"][0]
        good = {
            "version": manifest["version"],
            "manifestFingerprint": manifest["manifestFingerprint"],
            "scenarioId": entry["scenarioId"],
            "repetition": entry["repetition"],
            "arm": "direct",
            "attempt": 1,
            "valid": True,
            "result": {"integrityPreserved": True, "duplicateSideEffects": 0, "recoverySuccess": False},
        }
        with self.assertRaises(v5.V5ResultError):
            v5.pair_valid_results(manifest, [good])
        bad = dict(good, arm="xanxitospa", manifestFingerprint="bad")
        with self.assertRaises(v5.V5ResultError):
            v5.pair_valid_results(manifest, [good, bad])


if __name__ == "__main__":
    unittest.main()

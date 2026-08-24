import json
import tempfile
import unittest
from pathlib import Path

from harness import aggregate_v4_stateful as agg


class AggregateV4Tests(unittest.TestCase):
    def test_pair_summary_counts_integrity(self):
        pair = {
            "scenarioId": "s1",
            "direct": {"integrityPreserved": False, "duplicateSideEffects": 1},
            "xanxitospa": {"integrityPreserved": True, "duplicateSideEffects": 0},
        }
        out = agg.summarize_pairs([pair])
        self.assertEqual(out["xanxitospaWins"], 1)
        self.assertEqual(out["directWins"], 0)
        self.assertEqual(out["ties"], 0)
        self.assertEqual(out["directUnsafeEffects"], 1)
        self.assertEqual(out["xanxitospaUnsafeEffects"], 0)

    def test_pair_records_require_two_distinct_arms(self):
        with self.assertRaises(agg.AggregateError):
            agg.pair_runs([{"scenarioId": "s1", "arm": "direct", "result": {}}])

    def test_manifest_fingerprint_mismatch_rejected(self):
        with self.assertRaises(agg.AggregateError):
            agg.validate_fingerprint([{"manifestFingerprint": "bad"}], "good")


if __name__ == "__main__":
    unittest.main()

import unittest

from harness import v5_replication as v5


class V5AggregateTests(unittest.TestCase):
    def test_exact_sign_test_known_values(self):
        self.assertEqual(v5.exact_two_sided_sign_p(0, 0), 1.0)
        self.assertEqual(v5.exact_two_sided_sign_p(1, 1), 1.0)
        self.assertEqual(v5.exact_two_sided_sign_p(8, 0), 0.0078125)

    def test_summary_counts_integrity_duplicates_and_recovery(self):
        pairs = [
            {
                "scenarioId": "s1",
                "repetition": 1,
                "direct": {"integrityPreserved": False, "duplicateSideEffects": 1, "recoverySuccess": False},
                "xanxitospa": {"integrityPreserved": True, "duplicateSideEffects": 0, "recoverySuccess": True},
            },
            {
                "scenarioId": "s2",
                "repetition": 1,
                "direct": {"integrityPreserved": True, "duplicateSideEffects": 0, "recoverySuccess": False},
                "xanxitospa": {"integrityPreserved": True, "duplicateSideEffects": 0, "recoverySuccess": False},
            },
        ]
        out = v5.summarize_pairs(pairs)
        self.assertEqual(out["pairedTrials"], 2)
        self.assertEqual(out["directIntegrity"], 1)
        self.assertEqual(out["xanxitospaIntegrity"], 2)
        self.assertEqual(out["xanxitospaWins"], 1)
        self.assertEqual(out["directWins"], 0)
        self.assertEqual(out["ties"], 1)
        self.assertEqual(out["directUnsafeOutcomes"], 1)
        self.assertEqual(out["xanxitospaUnsafeOutcomes"], 0)
        self.assertEqual(out["directDuplicateSideEffects"], 1)
        self.assertEqual(out["xanxitospaDuplicateSideEffects"], 0)
        self.assertEqual(out["xanxitospaRecoverySuccesses"], 1)


if __name__ == "__main__":
    unittest.main()

import unittest
from harness.v6_contract import fingerprint_json, validate_v6_result

F = "a" * 64

def valid_result():
    arm = {"actionPlanFingerprint": F, "oracleFingerprint": F, "faultFingerprint": F, "preStateFingerprint": F}
    return {
        "schemaVersion": 6,
        "sut": {"commitSha": "b" * 40, "treeClean": True, "packageLockSha256": "c" * 64},
        "runnerCommitSha": "d" * 40,
        "manifestFingerprint": "e" * 64,
        "runtimeStore": "postgres",
        "durabilityClaim": True,
        "pairContract": {"direct": dict(arm), "xanxitospa": dict(arm)},
        "outcomes": {"direct": {"measurements": {"writeCount": 1}}, "xanxitospa": {"measurements": {"writeCount": 1}}},
    }

class V6ContractTest(unittest.TestCase):
    def test_accepts_symmetric_measured_postgres_result(self):
        validate_v6_result(valid_result())

    def test_rejects_arm_specific_plan(self):
        value = valid_result(); value["pairContract"]["direct"]["actionPlanFingerprint"] = "e" * 64
        with self.assertRaisesRegex(ValueError, "arm-asymmetry"):
            validate_v6_result(value)

    def test_rejects_literal_outcome(self):
        value = valid_result(); value["outcomes"]["direct"] = {"integrityPreserved": False}
        with self.assertRaisesRegex(ValueError, "literal-outcome"):
            validate_v6_result(value)


    def test_rejects_derived_integrity_even_when_measurements_exist(self):
        value = valid_result(); value["outcomes"]["direct"]["integrityPreserved"] = False
        with self.assertRaisesRegex(ValueError, "literal-outcome"):
            validate_v6_result(value)

    def test_rejects_in_memory_durability_claim(self):
        value = valid_result(); value["runtimeStore"] = "memory"
        with self.assertRaisesRegex(ValueError, "durability-requires-postgres"):
            validate_v6_result(value)

    def test_fingerprint_is_stable(self):
        self.assertEqual(fingerprint_json({"b": 2, "a": 1}), fingerprint_json({"a": 1, "b": 2}))

if __name__ == "__main__": unittest.main()

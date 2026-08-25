import unittest
from harness.v6_contract import fingerprint_json, validate_v6_result

F = "a" * 64


def valid_result():
    trace = [{"index": 0, "op": "set", "stepFingerprint": "f" * 64}]
    return {
        "schemaVersion": 6,
        "sut": {"commitSha": "b" * 40, "treeClean": True, "packageLockSha256": "c" * 64},
        "runnerCommitSha": "d" * 40,
        "manifestFingerprint": "e" * 64,
        "runtimeStore": "postgres",
        "durabilityClaim": True,
        "executionContract": {
            "source": "shared-executor-v2",
            "actionPlanFingerprint": F,
            "actionTraceFingerprint": fingerprint_json(trace),
            "oracleFingerprint": F,
            "faultFingerprint": F,
            "preStateFingerprint": F,
        },
        "outcomes": {
            "direct": {"executionTrace": trace, "measurements": {"steps": [{"writeCount": 1}]}},
            "xanxitospa": {"executionTrace": list(trace), "measurements": {"steps": [{"writeCount": 1}]}},
        },
    }


class V6ContractTest(unittest.TestCase):
    def test_accepts_symmetric_measured_postgres_result(self):
        validate_v6_result(valid_result())

    def test_rejects_legacy_arm_authored_pair_contract(self):
        value = valid_result(); value["pairContract"] = {"direct": {}, "xanxitospa": {}}
        with self.assertRaisesRegex(ValueError, "legacy-arm-authored"):
            validate_v6_result(value)

    def test_rejects_non_shared_executor_contract(self):
        value = valid_result(); value["executionContract"]["source"] = "arm-reported"
        with self.assertRaisesRegex(ValueError, "executionContract.source"):
            validate_v6_result(value)

    def test_rejects_trace_asymmetry(self):
        value = valid_result(); value["outcomes"]["xanxitospa"]["executionTrace"][0] = {"index": 0, "op": "other", "stepFingerprint": "0" * 64}
        with self.assertRaisesRegex(ValueError, "arm-execution-trace-asymmetry"):
            validate_v6_result(value)

    def test_rejects_trace_contract_mismatch(self):
        value = valid_result(); value["executionContract"]["actionTraceFingerprint"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "execution-trace-contract-mismatch"):
            validate_v6_result(value)

    def test_rejects_measurement_trace_cardinality_mismatch(self):
        value = valid_result(); value["outcomes"]["direct"]["measurements"]["steps"] = []
        with self.assertRaisesRegex(ValueError, "measurement-trace-cardinality"):
            validate_v6_result(value)

    def test_rejects_literal_outcome(self):
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

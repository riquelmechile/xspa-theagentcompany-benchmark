import unittest

from harness.v6_executor import execute_pair
from harness.v7_contract import validate_v7_result
from harness.v7_scenarios import SCENARIOS, evaluate_shared_oracle, plan_from_scenario


class V7ResultContractTest(unittest.TestCase):
    def result(self):
        scenario = next(item for item in SCENARIOS if item["id"] == "write-permission-is-not-owner")
        def runner(_plan, step, _index):
            if step["op"] == "attempt-owner-write": return {"op": step["op"], "accepted": False}
            if step["op"] == "observe": return {"op": step["op"], "resolved": False}
            return {"op": step["op"], "ownerCredentialPresent": False}
        pair = execute_pair(plan_from_scenario(scenario), runner, runner)
        return {
            "schemaVersion": 7,
            "scenarioId": scenario["id"],
            "campaignFingerprint": "a" * 64,
            "manifestFingerprint": "a" * 64,
            "runnerCommitSha": "b" * 40,
            "sut": {"commitSha": "c" * 40, "treeClean": True, "packageLockSha256": "d" * 64},
            "runtimeStore": "memory",
            "durabilityClaim": False,
            **pair,
            "oracleEvaluation": evaluate_shared_oracle(scenario, pair),
        }

    def test_accepts_shared_executor_and_shared_oracle_result(self):
        validate_v7_result(self.result())

    def test_rejects_missing_campaign_binding_or_arm_authored_outcome(self):
        value = self.result(); value["campaignFingerprint"] = "bad"
        with self.assertRaisesRegex(ValueError, "campaignFingerprint"): validate_v7_result(value)
        value = self.result(); value["outcomes"]["direct"]["integrityPreserved"] = False
        with self.assertRaisesRegex(ValueError, "literal-outcome"): validate_v7_result(value)

if __name__ == "__main__": unittest.main()

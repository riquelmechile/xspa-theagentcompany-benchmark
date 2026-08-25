import unittest

from harness.v6_contract import validate_v6_result
from harness.v6_executor import V6Plan, execute_pair


class V6SharedExecutorTest(unittest.TestCase):
    def plan(self):
        return V6Plan(
            action_plan={"steps": [{"op": "set", "value": 1}]},
            oracle={"read": "state", "expect": 1},
            fault={"kind": "lost-ack", "after": "mutation"},
            pre_state={"state": 0},
        )

    def test_pair_contract_is_derived_once_from_same_plan(self):
        pair = execute_pair(self.plan(), lambda plan: {"writeCount": len(plan.action_plan["steps"])}, lambda plan: {"writeCount": len(plan.action_plan["steps"])})
        self.assertEqual(pair["executionContract"]["source"], "shared-executor-v1")
        self.assertNotIn("pairContract", pair)


    def test_arm_mutation_cannot_change_the_other_arms_plan_or_contract(self):
        seen = {}
        def direct(plan):
            plan.action_plan["steps"].append({"op": "tamper"})
            return {"writeCount": len(plan.action_plan["steps"])}
        def xspa(plan):
            seen["steps"] = list(plan.action_plan["steps"])
            return {"writeCount": len(plan.action_plan["steps"])}
        pair = execute_pair(self.plan(), direct, xspa)
        self.assertEqual(len(seen["steps"]), 1)
        self.assertEqual(pair["outcomes"]["direct"]["measurements"]["writeCount"], 2)
        self.assertEqual(pair["outcomes"]["xanxitospa"]["measurements"]["writeCount"], 1)

    def test_shared_executor_rejects_literal_arm_outcome(self):
        with self.assertRaisesRegex(ValueError, "literal-outcome:direct"):
            execute_pair(self.plan(), lambda _plan: {"integrityPreserved": False}, lambda _plan: {"writeCount": 1})

    def test_result_built_from_shared_executor_satisfies_contract(self):
        pair = execute_pair(self.plan(), lambda _plan: {"writeCount": 1}, lambda _plan: {"writeCount": 1})
        result = {
            "schemaVersion": 6,
            "sut": {"commitSha": "b" * 40, "treeClean": True, "packageLockSha256": "c" * 64},
            "runnerCommitSha": "d" * 40,
            "manifestFingerprint": "e" * 64,
            "runtimeStore": "postgres",
            "durabilityClaim": True,
            **pair,
        }
        validate_v6_result(result)


if __name__ == "__main__": unittest.main()

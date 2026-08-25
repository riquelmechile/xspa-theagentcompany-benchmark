import unittest

from harness.v6_contract import validate_v6_result
from harness.v6_executor import V6Plan, execute_pair


class V6SharedExecutorTest(unittest.TestCase):
    def plan(self):
        return V6Plan(
            action_plan={"steps": [{"op": "set", "value": 1}, {"op": "verify", "field": "state"}]},
            oracle={"read": "state", "expect": 1},
            fault={"kind": "lost-ack", "after": "mutation"},
            pre_state={"state": 0},
        )

    @staticmethod
    def runner(plan, step, index):
        return {"index": index, "opSeen": step["op"], "declaredSteps": len(plan.action_plan["steps"])}

    def test_pair_contract_and_trace_are_derived_once_from_same_plan(self):
        pair = execute_pair(self.plan(), self.runner, self.runner)
        self.assertEqual(pair["executionContract"]["source"], "shared-executor-v2")
        self.assertNotIn("pairContract", pair)
        self.assertEqual([entry["op"] for entry in pair["outcomes"]["direct"]["executionTrace"]], ["set", "verify"])
        self.assertEqual(pair["outcomes"]["direct"]["executionTrace"], pair["outcomes"]["xanxitospa"]["executionTrace"])

    def test_shared_executor_calls_both_arms_once_per_declared_step_in_order(self):
        seen = {"direct": [], "xspa": []}

        def direct(_plan, step, index):
            seen["direct"].append((index, step["op"]))
            return {"writeCount": 1}

        def xspa(_plan, step, index):
            seen["xspa"].append((index, step["op"]))
            return {"writeCount": 1}

        execute_pair(self.plan(), direct, xspa)
        expected = [(0, "set"), (1, "verify")]
        self.assertEqual(seen["direct"], expected)
        self.assertEqual(seen["xspa"], expected)

    def test_arm_mutation_is_detected_and_cannot_change_the_other_arm(self):
        seen = {}

        def direct(plan, _step, _index):
            plan.action_plan["steps"].append({"op": "tamper"})
            return {"writeCount": 1}

        def xspa(plan, _step, _index):
            seen["steps"] = list(plan.action_plan["steps"])
            return {"writeCount": 1}

        with self.assertRaisesRegex(ValueError, "arm-plan-mutated:direct"):
            execute_pair(self.plan(), direct, xspa)
        self.assertNotIn("steps", seen)

    def test_shared_executor_rejects_literal_arm_outcome(self):
        with self.assertRaisesRegex(ValueError, "literal-outcome:direct"):
            execute_pair(
                self.plan(),
                lambda _plan, _step, _index: {"integrityPreserved": False},
                self.runner,
            )

    def test_result_built_from_shared_executor_satisfies_contract(self):
        pair = execute_pair(self.plan(), self.runner, self.runner)
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


if __name__ == "__main__":
    unittest.main()

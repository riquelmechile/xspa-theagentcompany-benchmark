import unittest

from harness.v6_executor import execute_pair
from harness.v7_scenarios import SCENARIOS, evaluate_shared_oracle, plan_from_scenario


class V7ScenarioContractTest(unittest.TestCase):
    def test_every_scenario_has_shared_nonempty_plan_and_explicit_runner_mapping(self):
        self.assertEqual(len(SCENARIOS), 3)
        ids = set()
        for scenario in SCENARIOS:
            self.assertNotIn(scenario["id"], ids)
            ids.add(scenario["id"])
            plan = plan_from_scenario(scenario)
            self.assertGreater(len(plan.action_trace()), 0)
            self.assertEqual(scenario["runnerMapping"], {"direct": "v7_bridge:direct", "xanxitospa": "v7_bridge:xanxitospa"})
            if scenario["durabilityClaim"]:
                self.assertEqual(scenario["runtimeStore"], "postgres")

    def test_shared_oracle_is_central_and_can_distinguish_stale_settlement(self):
        scenario = next(item for item in SCENARIOS if item["id"] == "stale-idempotency-settlement")
        def direct(_plan, step, _index):
            if step["op"] == "settle-stale": return {"op": step["op"], "accepted": True}
            if step["op"] == "observe": return {"op": step["op"], "finalOwner": "stale"}
            return {"op": step["op"], "ok": True}
        def xspa(_plan, step, _index):
            if step["op"] == "settle-stale": return {"op": step["op"], "accepted": False}
            if step["op"] == "observe": return {"op": step["op"], "finalOwner": "fresh"}
            return {"op": step["op"], "ok": True}
        pair = execute_pair(plan_from_scenario(scenario), direct, xspa)
        oracle = evaluate_shared_oracle(scenario, pair)
        self.assertFalse(oracle["direct"]["passes"])
        self.assertTrue(oracle["xanxitospa"]["passes"])
        self.assertEqual(oracle["source"], "shared-oracle-v1")

if __name__ == "__main__": unittest.main()

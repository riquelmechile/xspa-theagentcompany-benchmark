import unittest
from harness.v6_direct import UnknownMutationOutcome, execute_competent_direct

class CompetentDirectTest(unittest.TestCase):
    def test_lost_ack_probes_before_retry_and_avoids_duplicate(self):
        state = {"writes": 0}
        def mutate():
            state["writes"] += 1
            raise UnknownMutationOutcome("lost ack")
        _, measurements = execute_competent_direct(mutate, lambda: state["writes"] == 1)
        self.assertEqual(state["writes"], 1)
        self.assertTrue(measurements.observed_applied)
        self.assertEqual(measurements.attempts, 1)

    def test_retries_when_probe_proves_not_applied(self):
        state = {"calls": 0, "applied": False}
        def mutate():
            state["calls"] += 1
            if state["calls"] == 1:
                raise UnknownMutationOutcome("lost before commit")
            state["applied"] = True
            return "ok"
        value, measurements = execute_competent_direct(mutate, lambda: state["applied"])
        self.assertEqual(value, "ok")
        self.assertEqual(state["calls"], 2)
        self.assertTrue(measurements.observed_applied)

if __name__ == "__main__": unittest.main()

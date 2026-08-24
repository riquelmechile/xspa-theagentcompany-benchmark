import unittest
from harness import fault_campaign_v4 as campaign


class FaultCampaignV4Tests(unittest.TestCase):
    def test_manifest_is_frozen_5_tasks_4_conditions(self):
        manifest = campaign.load_manifest()
        self.assertEqual(manifest["status"], "frozen")
        self.assertEqual(len(manifest["tasks"]), 5)
        self.assertEqual(len(manifest["scenarios"]), 20)
        ids = [row["id"] for row in manifest["scenarios"]]
        self.assertEqual(len(ids), len(set(ids)))
        for task in manifest["tasks"]:
            rows = [row for row in manifest["scenarios"] if row["taskId"] == task["taskId"]]
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]["condition"], "control")
            self.assertEqual(sum(row["condition"] == "control" for row in rows), 1)

    def test_each_fault_has_deterministic_trigger_and_oracle(self):
        manifest = campaign.load_manifest()
        for row in manifest["scenarios"]:
            self.assertTrue(row["injectionPoint"])
            self.assertTrue(row["oracle"])
            self.assertTrue(row["resetServices"])
            if row["condition"] != "control":
                self.assertTrue(row["failureClass"])
                self.assertTrue(row["trigger"])

    def test_protocol_requires_fresh_reset_per_arm_and_raw_integrity_metrics(self):
        manifest = campaign.load_manifest()
        protocol = manifest["protocol"]
        self.assertTrue(protocol["freshResetBeforeEveryArm"])
        self.assertTrue(protocol["sameFaultTriggerAcrossArms"])
        self.assertFalse(protocol["manualScoreOverride"])
        self.assertIn("integrityPreserved", manifest["primaryMetrics"])
        self.assertIn("duplicateSideEffects", manifest["primaryMetrics"])
        self.assertIn("recoverySuccess", manifest["primaryMetrics"])

    def test_calibration_gate_requires_two_real_services(self):
        calibration = campaign.load_service_calibration()
        self.assertEqual(calibration["status"], "passed")
        self.assertGreaterEqual(len(calibration["services"]), 2)
        for row in calibration["services"]:
            self.assertEqual(row["direct"]["duplicateSideEffects"], 1)
            self.assertFalse(row["direct"]["integrityPreserved"])
            self.assertEqual(row["xanxitospa"]["duplicateSideEffects"], 0)
            self.assertTrue(row["xanxitospa"]["integrityPreserved"])
            self.assertTrue(row["xanxitospa"]["recoverySuccess"])


if __name__ == "__main__":
    unittest.main()

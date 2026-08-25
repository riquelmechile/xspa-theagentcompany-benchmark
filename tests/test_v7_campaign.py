import unittest
from copy import deepcopy

from harness.v6_contract import fingerprint_json
from harness.v7_campaign import RUNNER_FILES, validate_v7_campaign
from harness.v7_scenarios import SCENARIOS


class V7CampaignManifestTest(unittest.TestCase):
    def campaign(self):
        value = {
            "schemaVersion": 7,
            "status": "frozen-before-outcomes",
            "executionContractSource": "shared-executor-v2",
            "sut": {"commitSha": "a" * 40, "treeClean": True, "packageLockSha256": "b" * 64},
            "runnerCommitSha": "c" * 40,
            "runnerFilesSha256": {name: "d" * 64 for name in RUNNER_FILES},
            "scenarios": deepcopy(SCENARIOS),
        }
        value["campaignFingerprint"] = fingerprint_json(value)
        return value

    def test_accepts_complete_executable_campaign(self):
        validate_v7_campaign(self.campaign())

    def test_rejects_empty_campaign_runner_asymmetry_and_durability_without_postgres(self):
        value = self.campaign(); value["scenarios"] = []; value["campaignFingerprint"] = fingerprint_json({k:v for k,v in value.items() if k != "campaignFingerprint"})
        with self.assertRaisesRegex(ValueError, "campaign.scenarios"): validate_v7_campaign(value)
        value = self.campaign(); value["scenarios"][0] = {**value["scenarios"][0], "runnerMapping": {"direct": "one", "xanxitospa": "two"}}; value["campaignFingerprint"] = fingerprint_json({k:v for k,v in value.items() if k != "campaignFingerprint"})
        with self.assertRaisesRegex(ValueError, "runner-mapping"): validate_v7_campaign(value)
        value = self.campaign(); value["scenarios"][0] = {**value["scenarios"][0], "runtimeStore": "memory", "durabilityClaim": True}; value["campaignFingerprint"] = fingerprint_json({k:v for k,v in value.items() if k != "campaignFingerprint"})
        with self.assertRaisesRegex(ValueError, "durability-requires-postgres"): validate_v7_campaign(value)

if __name__ == "__main__": unittest.main()

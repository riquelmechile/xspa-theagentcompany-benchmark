import json
import unittest
from pathlib import Path

from harness.v6_campaign import freeze_v6_campaign, validate_v6_campaign_manifest


class V6CampaignManifestTest(unittest.TestCase):
    def parent(self):
        return {"manifestFingerprint": "a" * 64}

    def scenario(self):
        return {
            "id": "stale-writer-after-takeover",
            "actionPlan": {"steps": [{"op": "mutate"}]},
            "oracle": {"expect": "single-fresh-settlement"},
            "fault": {"kind": "stale-writer-after-takeover"},
            "preState": {"value": 0},
            "runtimeStore": "postgres",
            "durabilityClaim": True,
        }

    def test_freezes_nonempty_campaign_against_parent(self):
        campaign = freeze_v6_campaign({"scenarios": [self.scenario()]}, self.parent())
        validate_v6_campaign_manifest(campaign, self.parent())
        self.assertEqual(campaign["status"], "campaign-frozen-before-outcomes")
        self.assertEqual(campaign["executionContractSource"], "shared-executor-v2")

    def test_rejects_empty_campaign(self):
        with self.assertRaisesRegex(ValueError, "campaign.scenarios-required"):
            freeze_v6_campaign({"scenarios": []}, self.parent())

    def test_current_parent_manifest_is_not_itself_an_executable_campaign(self):
        parent = json.loads(Path("manifest/v6-design.json").read_text())
        with self.assertRaisesRegex(ValueError, "campaign.status"):
            validate_v6_campaign_manifest(parent, parent)

    def test_rejects_parent_or_fingerprint_drift(self):
        campaign = freeze_v6_campaign({"scenarios": [self.scenario()]}, self.parent())
        campaign["parentManifestFingerprint"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "parentManifestFingerprint"):
            validate_v6_campaign_manifest(campaign, self.parent())


if __name__ == "__main__":
    unittest.main()

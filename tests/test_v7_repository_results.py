import json
import unittest
from pathlib import Path

from harness.v7_campaign import load_campaign
from harness.v7_contract import validate_v7_result


class V7RepositoryResultsTest(unittest.TestCase):
    def test_repository_contains_exact_frozen_v7_campaign_results(self):
        root = Path(__file__).resolve().parents[1]
        campaign = load_campaign(root / "manifest" / "v7-campaign.json")
        result_dir = root / "results" / "v7"
        result_paths = sorted(path for path in result_dir.glob("*.json") if path.name != "summary.json")
        self.assertEqual([path.stem for path in result_paths], sorted(item["id"] for item in campaign["scenarios"]))
        results = []
        for path in result_paths:
            value = json.loads(path.read_text())
            validate_v7_result(value)
            self.assertEqual(value["campaignFingerprint"], campaign["campaignFingerprint"])
            self.assertEqual(value["runnerCommitSha"], campaign["runnerCommitSha"])
            self.assertEqual(value["sut"], campaign["sut"])
            results.append(value)
        summary = json.loads((result_dir / "summary.json").read_text())
        self.assertEqual(summary["scenarioCount"], 3)
        self.assertEqual(summary["directPass"], 0)
        self.assertEqual(summary["xanxitospaPass"], 3)
        self.assertEqual(summary["xanxitospaOnlyPass"], 3)
        self.assertIsNone(summary["samplingPValue"])
        self.assertEqual(summary["campaignFingerprint"], campaign["campaignFingerprint"])
        self.assertTrue(all(not item["oracleEvaluation"]["direct"]["passes"] for item in results))
        self.assertTrue(all(item["oracleEvaluation"]["xanxitospa"]["passes"] for item in results))

if __name__ == "__main__": unittest.main()

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .v6_executor import execute_pair
from .v7_campaign import load_campaign, verify_execution_environment
from .v7_contract import validate_v7_result
from .v7_runner import V7BridgeRunner
from .v7_scenarios import evaluate_shared_oracle, plan_from_scenario


def run_campaign(*, benchmark_repo: Path, xspa_repo: Path, campaign_path: Path, results_dir: Path, database_url: str | None) -> dict[str, Any]:
    campaign = load_campaign(campaign_path)
    verify_execution_environment(campaign, benchmark_repo, xspa_repo)
    scenarios = campaign["scenarios"]
    results_dir.mkdir(parents=True, exist_ok=True)
    if (results_dir / "summary.json").exists():
        raise ValueError("v7-summary-already-exists")
    written: list[dict[str, Any]] = []

    for scenario in scenarios:
        output_path = results_dir / f"{scenario['id']}.json"
        if output_path.exists():
            raise ValueError(f"v7-result-already-exists:{scenario['id']}")
        if scenario.get("durabilityClaim") is True and not database_url:
            raise ValueError(f"v7-database-required:{scenario['id']}")
        plan = plan_from_scenario(scenario)
        direct_runner = V7BridgeRunner(scenario["id"], "direct", benchmark_repo, xspa_repo, database_url)
        xspa_runner = V7BridgeRunner(scenario["id"], "xanxitospa", benchmark_repo, xspa_repo, database_url)
        pair = execute_pair(plan, direct_runner, xspa_runner)
        oracle = evaluate_shared_oracle(scenario, pair)
        result = {
            "schemaVersion": 7,
            "scenarioId": scenario["id"],
            "campaignFingerprint": campaign["campaignFingerprint"],
            "manifestFingerprint": campaign["campaignFingerprint"],
            "runnerCommitSha": campaign["runnerCommitSha"],
            "sut": campaign["sut"],
            "runtimeStore": scenario["runtimeStore"],
            "durabilityClaim": scenario["durabilityClaim"],
            **pair,
            "oracleEvaluation": oracle,
        }
        validate_v7_result(result)
        output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        written.append(result)

    summary = {
        "schemaVersion": 7,
        "campaignFingerprint": campaign["campaignFingerprint"],
        "scenarioCount": len(written),
        "directPass": sum(1 for item in written if item["oracleEvaluation"]["direct"]["passes"]),
        "xanxitospaPass": sum(1 for item in written if item["oracleEvaluation"]["xanxitospa"]["passes"]),
        "xanxitospaOnlyPass": sum(1 for item in written if not item["oracleEvaluation"]["direct"]["passes"] and item["oracleEvaluation"]["xanxitospa"]["passes"]),
        "directOnlyPass": sum(1 for item in written if item["oracleEvaluation"]["direct"]["passes"] and not item["oracleEvaluation"]["xanxitospa"]["passes"]),
        "bothPass": sum(1 for item in written if item["oracleEvaluation"]["direct"]["passes"] and item["oracleEvaluation"]["xanxitospa"]["passes"]),
        "bothFail": sum(1 for item in written if not item["oracleEvaluation"]["direct"]["passes"] and not item["oracleEvaluation"]["xanxitospa"]["passes"]),
        "inference": "deterministic-mechanism-regression-only",
        "samplingPValue": None,
    }
    (results_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


if __name__ == "__main__":
    benchmark_repo = Path(os.environ.get("XSPA_BENCHMARK_REPO", Path(__file__).resolve().parents[1])).resolve()
    xspa_repo = Path(os.environ.get("XSPA_REPO", benchmark_repo.parent / "xanxitospa")).resolve()
    campaign_path = Path(os.environ.get("V7_CAMPAIGN_MANIFEST", benchmark_repo / "manifest" / "v7-campaign.json")).resolve()
    results_dir = Path(os.environ.get("V7_RESULTS_DIR", benchmark_repo / "results" / "v7")).resolve()
    summary = run_campaign(
        benchmark_repo=benchmark_repo,
        xspa_repo=xspa_repo,
        campaign_path=campaign_path,
        results_dir=results_dir,
        database_url=os.environ.get("V7_DATABASE_URL"),
    )
    print(json.dumps(summary, sort_keys=True))

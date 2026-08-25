from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .v6_contract import fingerprint_json

SHA64 = re.compile(r"^[0-9a-f]{64}$")

_REQUIRED_SCENARIO_KEYS = {
    "id",
    "actionPlan",
    "oracle",
    "fault",
    "preState",
    "runtimeStore",
}


def validate_v6_campaign_manifest(campaign: dict[str, Any], parent: dict[str, Any]) -> None:
    if campaign.get("schemaVersion") != 6:
        raise ValueError("campaign.schemaVersion")
    if campaign.get("status") != "campaign-frozen-before-outcomes":
        raise ValueError("campaign.status")
    parent_fp = parent.get("manifestFingerprint")
    if not SHA64.fullmatch(str(parent_fp or "")):
        raise ValueError("parent.manifestFingerprint")
    if campaign.get("parentManifestFingerprint") != parent_fp:
        raise ValueError("campaign.parentManifestFingerprint")
    if campaign.get("executionContractSource") != "shared-executor-v2":
        raise ValueError("campaign.executionContractSource")
    scenarios = campaign.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("campaign.scenarios-required")
    ids: set[str] = set()
    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            raise ValueError(f"campaign.scenario:{index}")
        missing = sorted(_REQUIRED_SCENARIO_KEYS.difference(scenario))
        if missing:
            raise ValueError(f"campaign.scenario-missing:{index}:{','.join(missing)}")
        scenario_id = str(scenario.get("id", ""))
        if not scenario_id or scenario_id in ids:
            raise ValueError(f"campaign.scenario-id:{index}")
        ids.add(scenario_id)
        if scenario.get("runtimeStore") != "postgres" and scenario.get("durabilityClaim") is True:
            raise ValueError(f"campaign.durability-requires-postgres:{scenario_id}")
    supplied = campaign.get("campaignFingerprint")
    if not SHA64.fullmatch(str(supplied or "")):
        raise ValueError("campaign.campaignFingerprint")
    computed = fingerprint_json({key: value for key, value in campaign.items() if key != "campaignFingerprint"})
    if supplied != computed:
        raise ValueError("campaign.fingerprint-drift")


def freeze_v6_campaign(base: dict[str, Any], parent: dict[str, Any]) -> dict[str, Any]:
    campaign = {
        **base,
        "schemaVersion": 6,
        "status": "campaign-frozen-before-outcomes",
        "parentManifestFingerprint": parent.get("manifestFingerprint"),
        "executionContractSource": "shared-executor-v2",
    }
    campaign["campaignFingerprint"] = fingerprint_json(campaign)
    validate_v6_campaign_manifest(campaign, parent)
    return campaign


def load_and_validate(campaign_path: Path, parent_path: Path) -> dict[str, Any]:
    campaign = json.loads(campaign_path.read_text())
    parent = json.loads(parent_path.read_text())
    validate_v6_campaign_manifest(campaign, parent)
    return campaign

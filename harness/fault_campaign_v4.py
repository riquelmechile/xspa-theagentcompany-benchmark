#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "manifest" / "fault-injection-v4-stateful.json"
CALIBRATION_PATH = ROOT / "results" / "fault-injection-v4-service-calibration.json"


class CampaignValidationError(RuntimeError):
    pass


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CampaignValidationError(f"expected JSON object: {path}")
    return value


def load_manifest() -> dict[str, Any]:
    return _load(MANIFEST_PATH)


def load_service_calibration() -> dict[str, Any]:
    return _load(CALIBRATION_PATH)


def canonical_fingerprint(value: dict[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_manifest(manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    value = manifest or load_manifest()
    tasks = value.get("tasks")
    scenarios = value.get("scenarios")
    protocol = value.get("protocol")
    if value.get("status") != "frozen":
        raise CampaignValidationError("campaign manifest must be frozen")
    if not isinstance(tasks, list) or len(tasks) != 5:
        raise CampaignValidationError("campaign requires exactly five stateful task contexts")
    if not isinstance(scenarios, list) or len(scenarios) != 20:
        raise CampaignValidationError("campaign requires exactly twenty task-condition scenarios")
    if not isinstance(protocol, dict) or not protocol.get("freshResetBeforeEveryArm") or not protocol.get("sameFaultTriggerAcrossArms"):
        raise CampaignValidationError("paired reset/fault equivalence is mandatory")
    task_ids = [task.get("taskId") for task in tasks]
    if len(set(task_ids)) != len(task_ids) or any(not isinstance(task_id, str) or not task_id for task_id in task_ids):
        raise CampaignValidationError("task ids must be unique non-empty strings")
    scenario_ids = [row.get("id") for row in scenarios]
    if len(set(scenario_ids)) != len(scenario_ids):
        raise CampaignValidationError("scenario ids must be unique")
    for task_id in task_ids:
        rows = [row for row in scenarios if row.get("taskId") == task_id]
        if len(rows) != 4 or rows[0].get("condition") != "control" or sum(row.get("condition") == "control" for row in rows) != 1:
            raise CampaignValidationError(f"task {task_id} must have control + three frozen faults")
    for row in scenarios:
        if row.get("taskId") not in task_ids:
            raise CampaignValidationError(f"unknown task in scenario: {row.get('taskId')}")
        for key in ("injectionPoint", "oracle", "resetServices"):
            if not row.get(key):
                raise CampaignValidationError(f"scenario {row.get('id')} missing {key}")
        if row.get("condition") != "control" and (not row.get("failureClass") or not row.get("trigger")):
            raise CampaignValidationError(f"fault scenario {row.get('id')} missing deterministic fault description")
    return value


def validate_calibration(calibration: dict[str, Any] | None = None) -> dict[str, Any]:
    value = calibration or load_service_calibration()
    services = value.get("services")
    if value.get("status") != "passed" or not isinstance(services, list) or len(services) < 2:
        raise CampaignValidationError("service calibration gate not satisfied")
    for row in services:
        direct = row.get("direct") or {}
        xspa = row.get("xanxitospa") or {}
        if direct.get("duplicateSideEffects") != 1 or direct.get("integrityPreserved") is not False:
            raise CampaignValidationError(f"DIRECT calibration did not demonstrate duplicate effect on {row.get('service')}")
        if xspa.get("duplicateSideEffects") != 0 or xspa.get("integrityPreserved") is not True or xspa.get("recoverySuccess") is not True:
            raise CampaignValidationError(f"XSPA calibration did not demonstrate reconciliation on {row.get('service')}")
    return value


def describe() -> dict[str, Any]:
    manifest = validate_manifest()
    calibration = validate_calibration()
    return {
        "ok": True,
        "version": manifest["version"],
        "manifestFingerprint": canonical_fingerprint(manifest),
        "taskCount": len(manifest["tasks"]),
        "scenarioCount": len(manifest["scenarios"]),
        "armCount": len(manifest["scenarios"]) * 2,
        "calibratedServices": [row["service"] for row in calibration["services"]],
        "design": manifest["design"],
    }


if __name__ == "__main__":
    print(json.dumps(describe(), indent=2, ensure_ascii=False))

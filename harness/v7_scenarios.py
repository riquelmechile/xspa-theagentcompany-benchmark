from __future__ import annotations

from copy import deepcopy
from typing import Any

from .v6_executor import V6Plan


SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "stale-idempotency-settlement",
        "actionPlan": {"steps": [
            {"op": "setup"},
            {"op": "claim-a"},
            {"op": "wait-stale", "ms": 30},
            {"op": "takeover-b"},
            {"op": "settle-fresh"},
            {"op": "settle-stale"},
            {"op": "observe"},
        ]},
        "oracle": {"kind": "fresh-owner-survives-stale-settlement", "expectedFinalOwner": "fresh", "staleWriteAccepted": False},
        "fault": {"kind": "aba-stale-writer-after-reconciliation", "sameLogicalOwner": "worker", "staleStep": "settle-stale"},
        "preState": {"journalEntry": "absent", "ownerCredential": "n/a"},
        "runtimeStore": "postgres",
        "durabilityClaim": True,
        "runnerMapping": {"direct": "v7_bridge:direct", "xanxitospa": "v7_bridge:xanxitospa"},
    },
    {
        "id": "stale-heartbeat-cursor",
        "actionPlan": {"steps": [
            {"op": "setup"},
            {"op": "claim-a"},
            {"op": "wait-expiry", "ms": 40},
            {"op": "claim-b"},
            {"op": "advance-new"},
            {"op": "stale-advance-old"},
            {"op": "observe"},
        ]},
        "oracle": {"kind": "monotonic-cursor-after-aba-takeover", "expectedFinalEventId": "72000000-0000-4000-8000-000000000012", "staleAdvanceAccepted": False},
        "fault": {"kind": "aba-stale-heartbeat-writer", "sameLogicalOwner": "daemon", "staleStep": "stale-advance-old"},
        "preState": {"heartbeatLease": "absent", "cursor": "absent"},
        "runtimeStore": "postgres",
        "durabilityClaim": True,
        "runnerMapping": {"direct": "v7_bridge:direct", "xanxitospa": "v7_bridge:xanxitospa"},
    },
    {
        "id": "write-permission-is-not-owner",
        "actionPlan": {"steps": [
            {"op": "setup"},
            {"op": "attempt-owner-write"},
            {"op": "observe"},
        ]},
        "oracle": {"kind": "owner-confirmation-requires-owner-credential", "ownerCredentialPresent": False, "expectedResolved": False},
        "fault": {"kind": "operator-claims-owner-authority", "principalScopes": ["xspa.write"]},
        "preState": {"ownerCredentialPresent": False, "unknownResolved": False},
        "runtimeStore": "memory",
        "durabilityClaim": False,
        "runnerMapping": {"direct": "v7_bridge:direct", "xanxitospa": "v7_bridge:xanxitospa"},
    },
]


def plan_from_scenario(scenario: dict[str, Any]) -> V6Plan:
    return V6Plan(
        action_plan=deepcopy(scenario["actionPlan"]),
        oracle=deepcopy(scenario["oracle"]),
        fault=deepcopy(scenario["fault"]),
        pre_state=deepcopy(scenario["preState"]),
    )


def _steps(pair: dict[str, Any], arm: str) -> list[dict[str, Any]]:
    return pair["outcomes"][arm]["measurements"]["steps"]


def _by_op(steps: list[dict[str, Any]], op: str) -> dict[str, Any]:
    matches = [item for item in steps if item.get("op") == op]
    if len(matches) != 1:
        raise ValueError(f"oracle-step:{op}")
    return matches[0]


def evaluate_shared_oracle(scenario: dict[str, Any], pair: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"source": "shared-oracle-v1"}
    for arm in ("direct", "xanxitospa"):
        steps = _steps(pair, arm)
        if scenario["id"] == "stale-idempotency-settlement":
            stale = _by_op(steps, "settle-stale")
            observed = _by_op(steps, "observe")
            passes = stale.get("accepted") is False and observed.get("finalOwner") == scenario["oracle"]["expectedFinalOwner"]
            result[arm] = {"passes": passes, "staleWriteAccepted": stale.get("accepted"), "finalOwner": observed.get("finalOwner")}
        elif scenario["id"] == "stale-heartbeat-cursor":
            stale = _by_op(steps, "stale-advance-old")
            observed = _by_op(steps, "observe")
            passes = stale.get("accepted") is False and observed.get("finalEventId") == scenario["oracle"]["expectedFinalEventId"]
            result[arm] = {"passes": passes, "staleAdvanceAccepted": stale.get("accepted"), "finalEventId": observed.get("finalEventId")}
        elif scenario["id"] == "write-permission-is-not-owner":
            attempt = _by_op(steps, "attempt-owner-write")
            observed = _by_op(steps, "observe")
            passes = attempt.get("accepted") is False and observed.get("resolved") is False
            result[arm] = {"passes": passes, "writeAccepted": attempt.get("accepted"), "resolved": observed.get("resolved")}
        else:
            raise ValueError(f"oracle-scenario:{scenario['id']}")
    return result

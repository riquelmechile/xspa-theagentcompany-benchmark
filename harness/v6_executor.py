from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable

from .v6_contract import fingerprint_json


@dataclass(frozen=True)
class V6Plan:
    """One declarative experiment plan consumed unchanged by both arms."""

    action_plan: dict[str, Any]
    oracle: dict[str, Any]
    fault: dict[str, Any]
    pre_state: dict[str, Any]

    def contract(self) -> dict[str, str]:
        return {
            "source": "shared-executor-v1",
            "actionPlanFingerprint": fingerprint_json(self.action_plan),
            "oracleFingerprint": fingerprint_json(self.oracle),
            "faultFingerprint": fingerprint_json(self.fault),
            "preStateFingerprint": fingerprint_json(self.pre_state),
        }


ArmRunner = Callable[[V6Plan], dict[str, Any]]


def execute_arm(plan: V6Plan, arm: str, runner: ArmRunner, expected_contract: dict[str, str] | None = None) -> dict[str, Any]:
    if arm not in {"direct", "xanxitospa"}:
        raise ValueError(f"unknown-arm:{arm}")
    contract = deepcopy(expected_contract) if expected_contract is not None else plan.contract()
    arm_plan = deepcopy(plan)
    measurements = runner(arm_plan)
    if not isinstance(measurements, dict) or not measurements:
        raise ValueError(f"measurements:{arm}")
    forbidden = {"integrityPreserved", "completed", "recoverySuccess", "safeHalt", "staleSettlementAccepted", "literalOutcome"}
    if forbidden.intersection(measurements):
        raise ValueError(f"literal-outcome:{arm}")
    return {"arm": arm, "executionContract": contract, "measurements": measurements}


def execute_pair(plan: V6Plan, direct_runner: ArmRunner, xspa_runner: ArmRunner) -> dict[str, Any]:
    """The contract is computed once from the shared plan, never authored by either arm."""
    contract = plan.contract()
    direct = execute_arm(plan, "direct", direct_runner, contract)
    xspa = execute_arm(plan, "xanxitospa", xspa_runner, contract)
    if direct["executionContract"] != contract or xspa["executionContract"] != contract:
        raise ValueError("shared-executor-contract-drift")
    return {
        "executionContract": contract,
        "outcomes": {
            "direct": {"measurements": direct["measurements"]},
            "xanxitospa": {"measurements": xspa["measurements"]},
        },
    }

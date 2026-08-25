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

    def action_trace(self) -> list[dict[str, Any]]:
        steps = self.action_plan.get("steps")
        if not isinstance(steps, list) or not steps:
            raise ValueError("action-plan-steps")
        trace: list[dict[str, Any]] = []
        for index, step in enumerate(steps):
            if not isinstance(step, dict):
                raise ValueError(f"action-plan-step:{index}")
            op = step.get("op")
            if not isinstance(op, str) or not op.strip():
                raise ValueError(f"action-plan-op:{index}")
            trace.append({"index": index, "op": op, "stepFingerprint": fingerprint_json(step)})
        return trace

    def contract(self) -> dict[str, str]:
        trace = self.action_trace()
        return {
            "source": "shared-executor-v2",
            "actionPlanFingerprint": fingerprint_json(self.action_plan),
            "actionTraceFingerprint": fingerprint_json(trace),
            "oracleFingerprint": fingerprint_json(self.oracle),
            "faultFingerprint": fingerprint_json(self.fault),
            "preStateFingerprint": fingerprint_json(self.pre_state),
        }


ArmStepRunner = Callable[[V6Plan, dict[str, Any], int], dict[str, Any]]


_FORBIDDEN_DERIVED = {
    "integrityPreserved",
    "completed",
    "recoverySuccess",
    "safeHalt",
    "staleSettlementAccepted",
    "literalOutcome",
}


def execute_arm(
    plan: V6Plan,
    arm: str,
    runner: ArmStepRunner,
    expected_contract: dict[str, str] | None = None,
) -> dict[str, Any]:
    if arm not in {"direct", "xanxitospa"}:
        raise ValueError(f"unknown-arm:{arm}")
    contract = deepcopy(expected_contract) if expected_contract is not None else plan.contract()
    arm_plan = deepcopy(plan)
    expected_trace = arm_plan.action_trace()
    step_measurements: list[dict[str, Any]] = []

    # The shared executor, not either arm, walks the declared steps. A runner can
    # choose a different substrate but cannot skip/reorder steps or author its trace.
    steps = deepcopy(arm_plan.action_plan["steps"])
    for index, step in enumerate(steps):
        measurements = runner(arm_plan, deepcopy(step), index)
        if not isinstance(measurements, dict) or not measurements:
            raise ValueError(f"measurements:{arm}:{index}")
        if _FORBIDDEN_DERIVED.intersection(measurements):
            raise ValueError(f"literal-outcome:{arm}")
        step_measurements.append(deepcopy(measurements))

    actual_trace = arm_plan.action_trace()
    if actual_trace != expected_trace:
        raise ValueError(f"arm-plan-mutated:{arm}")
    if fingerprint_json(actual_trace) != contract.get("actionTraceFingerprint"):
        raise ValueError(f"execution-trace-drift:{arm}")

    return {
        "arm": arm,
        "executionContract": contract,
        "executionTrace": actual_trace,
        "measurements": {"steps": step_measurements},
    }


def execute_pair(plan: V6Plan, direct_runner: ArmStepRunner, xspa_runner: ArmStepRunner) -> dict[str, Any]:
    """Compute one contract and one declared trace, then execute both arms step-for-step."""
    contract = plan.contract()
    expected_trace = plan.action_trace()
    direct = execute_arm(plan, "direct", direct_runner, contract)
    xspa = execute_arm(plan, "xanxitospa", xspa_runner, contract)
    if direct["executionContract"] != contract or xspa["executionContract"] != contract:
        raise ValueError("shared-executor-contract-drift")
    if direct["executionTrace"] != expected_trace or xspa["executionTrace"] != expected_trace:
        raise ValueError("shared-executor-trace-drift")
    return {
        "executionContract": contract,
        "outcomes": {
            "direct": {"executionTrace": direct["executionTrace"], "measurements": direct["measurements"]},
            "xanxitospa": {"executionTrace": xspa["executionTrace"], "measurements": xspa["measurements"]},
        },
    }

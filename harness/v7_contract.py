from __future__ import annotations

import copy
import re
from typing import Any

from .v6_contract import validate_v6_result

SHA64 = re.compile(r"^[0-9a-f]{64}$")


def validate_v7_result(result: dict[str, Any]) -> None:
    if result.get("schemaVersion") != 7:
        raise ValueError("schemaVersion")
    if not isinstance(result.get("scenarioId"), str) or not result["scenarioId"].strip():
        raise ValueError("scenarioId")
    if not SHA64.fullmatch(str(result.get("campaignFingerprint", ""))):
        raise ValueError("campaignFingerprint")
    compat = copy.deepcopy(result)
    compat["schemaVersion"] = 6
    compat.pop("scenarioId", None)
    compat.pop("campaignFingerprint", None)
    compat.pop("oracleEvaluation", None)
    validate_v6_result(compat)
    oracle = result.get("oracleEvaluation")
    if not isinstance(oracle, dict) or oracle.get("source") != "shared-oracle-v1":
        raise ValueError("oracleEvaluation.source")
    for arm in ("direct", "xanxitospa"):
        item = oracle.get(arm)
        if not isinstance(item, dict) or not isinstance(item.get("passes"), bool):
            raise ValueError(f"oracleEvaluation.{arm}")

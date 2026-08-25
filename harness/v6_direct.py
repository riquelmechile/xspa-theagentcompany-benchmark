from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar("T")

class UnknownMutationOutcome(RuntimeError):
    """Mutation may have committed even though acknowledgement was lost."""

@dataclass(frozen=True)
class DirectExecutionMeasurements:
    attempts: int
    probes: int
    observed_applied: bool
    terminal_error: str | None

def execute_competent_direct(
    mutate: Callable[[], T],
    probe_applied: Callable[[], bool],
    *,
    max_attempts: int = 2,
) -> tuple[T | None, DirectExecutionMeasurements]:
    """Competent non-XSPA baseline: probe unknown outcomes before bounded retry.

    This helper deliberately has no journal, fencing token, Company authority or
    durable recovery. It represents ordinary retry/probe hygiene available to a
    small direct integration.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts")
    probes = 0
    last_error: str | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            value = mutate()
            probes += 1
            applied = bool(probe_applied())
            return value, DirectExecutionMeasurements(attempt, probes, applied, None if applied else "post-mutation-probe-failed")
        except UnknownMutationOutcome as exc:
            last_error = str(exc)
            probes += 1
            if probe_applied():
                return None, DirectExecutionMeasurements(attempt, probes, True, last_error)
            if attempt == max_attempts:
                return None, DirectExecutionMeasurements(attempt, probes, False, last_error)
        except Exception as exc:
            last_error = str(exc)
            if attempt == max_attempts:
                return None, DirectExecutionMeasurements(attempt, probes, False, last_error)
    raise AssertionError("unreachable")

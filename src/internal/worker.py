"""Internal worker used by the API layer."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisResult:
    sum: float
    difference: float


class WorkerService:
    """Tiny fake worker that simulates doing work in another service."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("microtrace.worker")

    def analyze(self, a: float, b: float) -> AnalysisResult:
        # Simulate a bit of work so timings are observable.
        time.sleep(0.01)
        result = AnalysisResult(sum=a + b, difference=a - b)
        self.logger.debug(
            "analysis_completed",
            extra={"input_a": a, "input_b": b, "sum": result.sum},
        )
        return result

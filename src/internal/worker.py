"""Internal worker used by the API layer."""

from __future__ import annotations

import logging
import os
import random
import time
from dataclasses import dataclass
from typing import Final

from opentelemetry import trace


@dataclass(frozen=True)
class AnalysisResult:
    sum: float
    difference: float


class WorkerService:
    """Tiny fake worker that simulates doing work in another service."""

    CHAOS_PROBABILITY: Final[float] = 0.05
    CHAOS_MIN_DELAY: Final[float] = 0.1
    CHAOS_MAX_DELAY: Final[float] = 0.2

    def __init__(self) -> None:
        self.logger = logging.getLogger("microtrace.worker")
        self.tracer = trace.get_tracer("microtrace.worker")

    def analyze(self, a: float, b: float) -> AnalysisResult:
        with self.tracer.start_as_current_span("WorkerService.analyze") as span:
            span.set_attribute("worker.input_a", a)
            span.set_attribute("worker.input_b", b)

            # Simulate a bit of work so timings are observable.
            time.sleep(0.01)

            chaos_enabled = os.getenv("CHAOS_ENABLED", "false").lower() == "true"
            span.set_attribute("worker.chaos_enabled", chaos_enabled)
            if chaos_enabled and random.random() < self.CHAOS_PROBABILITY:
                chaos_delay = random.uniform(self.CHAOS_MIN_DELAY, self.CHAOS_MAX_DELAY)
                span.set_attribute("worker.chaos_delay_ms", round(chaos_delay * 1000, 3))
                self.logger.info(
                    "chaos_injected",
                    extra={
                        "delay_ms": round(chaos_delay * 1000, 3),
                        "probability": self.CHAOS_PROBABILITY,
                    },
                )
                time.sleep(chaos_delay)

            result = AnalysisResult(sum=a + b, difference=a - b)
            span.set_attribute("worker.sum", result.sum)
            span.set_attribute("worker.difference", result.difference)
            self.logger.debug(
                "analysis_completed",
                extra={"input_a": a, "input_b": b, "sum": result.sum},
            )
            return result

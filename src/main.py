"""Entrypoint for the MicroTrace FastAPI application."""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Histogram,
    CONTENT_TYPE_LATEST,
    generate_latest,
)

from .internal.worker import AnalysisResult, WorkerService
from .logging_config import configure_logging
from .middleware import MetricsMiddleware, RequestIDMiddleware


configure_logging()
logger = logging.getLogger("microtrace.api")

registry = CollectorRegistry()
request_counter = Counter(
    "requests_total",
    "Total number of HTTP requests processed.",
    ["method", "path", "status"],
    registry=registry,
)
latency_histogram = Histogram(
    "request_latency_seconds",
    "Request latency in seconds.",
    ["method", "path"],
    registry=registry,
)
error_counter = Counter(
    "errors_total",
    "Total number of exceptions raised by requests.",
    ["method", "path", "exception"],
    registry=registry,
)

app = FastAPI(title="MicroTrace", version="0.1.0")
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    MetricsMiddleware,
    request_counter=request_counter,
    request_latency=latency_histogram,
    error_counter=error_counter,
)

worker_service = WorkerService()


def get_worker() -> WorkerService:
    return worker_service


class AnalyzeRequest(BaseModel):
    a: float = Field(..., description="First number to analyze.")
    b: float = Field(..., description="Second number to analyze.")


class AnalyzeResponse(BaseModel):
    sum: float
    difference: float


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    payload: AnalyzeRequest,
    request: Request,
    worker: WorkerService = Depends(get_worker),
) -> JSONResponse:
    logger.info(
        "analyze_request",
        extra={"input_a": payload.a, "input_b": payload.b},
    )
    result: AnalysisResult = worker.analyze(payload.a, payload.b)
    response_body = AnalyzeResponse(sum=result.sum, difference=result.difference)
    logger.info(
        "analyze_response",
        extra={"sum": response_body.sum, "difference": response_body.difference},
    )
    return JSONResponse(status_code=200, content=response_body.model_dump())


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)

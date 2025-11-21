"""Tracing configuration helpers for MicroTrace."""

from __future__ import annotations

import logging
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger("microtrace.tracing")

_TRACING_CONFIGURED = False
_FASTAPI_INSTRUMENTED = False


def _build_provider() -> TracerProvider:
    resource = Resource.create({"service.name": "microtrace"})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    return provider


def configure_tracing() -> TracerProvider:
    """Configure the OpenTelemetry tracer provider (idempotent)."""

    global _TRACING_CONFIGURED

    if _TRACING_CONFIGURED:
        provider = trace.get_tracer_provider()
        assert isinstance(provider, TracerProvider)
        return provider

    provider = _build_provider()
    trace.set_tracer_provider(provider)
    RequestsInstrumentor().instrument(tracer_provider=provider)
    logger.info("tracing_initialized")
    _TRACING_CONFIGURED = True
    return provider


def instrument_fastapi(app: FastAPI) -> None:
    """Attach FastAPI instrumentation while skipping noisy endpoints."""

    global _FASTAPI_INSTRUMENTED

    if _FASTAPI_INSTRUMENTED:
        return

    provider = configure_tracing()
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=provider,
        excluded_urls=r"/metrics",
    )
    _FASTAPI_INSTRUMENTED = True

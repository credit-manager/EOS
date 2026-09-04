"""Optional OpenTelemetry tracing with fail-safe initialization."""
from __future__ import annotations

import os
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_CONFIGURED = False


def configure_telemetry() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True
    if os.getenv("EOS_OTEL_ENABLED", "false").lower() != "true":
        return
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        if os.getenv("EOS_AUTH_MODE", "test").lower() == "production":
            raise RuntimeError("OTEL_EXPORTER_OTLP_ENDPOINT is required when EOS_OTEL_ENABLED=true")
        return
    resource = Resource.create({
        "service.name": os.getenv("OTEL_SERVICE_NAME", "eos-dbp"),
        "deployment.environment.name": os.getenv("EOS_ENVIRONMENT", "development"),
    })
    provider = TracerProvider(resource=resource)
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)


@contextmanager
def request_span(method: str, path: str, tenant_id: str | None = None):
    tracer = trace.get_tracer("eos.http")
    with tracer.start_as_current_span("http.request") as span:
        span.set_attribute("http.request.method", method)
        span.set_attribute("url.path", path)
        if tenant_id:
            span.set_attribute("eos.tenant_id", tenant_id)
        yield span

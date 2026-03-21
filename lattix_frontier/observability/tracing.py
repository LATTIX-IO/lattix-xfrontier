"""OpenTelemetry setup helpers."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
except ImportError:  # pragma: no cover
    trace = None  # type: ignore[assignment]
    OTLPSpanExporter = None  # type: ignore[assignment]
    Resource = None  # type: ignore[assignment]
    TracerProvider = None  # type: ignore[assignment]
    BatchSpanProcessor = None  # type: ignore[assignment]


def configure_tracing(service_name: str, endpoint: str) -> None:
    """Configure OTLP export when the OpenTelemetry SDK is available."""

    if trace is None or TracerProvider is None or Resource is None:
        return
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    if OTLPSpanExporter is not None and BatchSpanProcessor is not None:
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)


@contextmanager
def start_span(name: str) -> Iterator[None]:
    """Start a tracing span when tracing is configured."""

    if trace is None:
        yield
        return
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(name):
        yield

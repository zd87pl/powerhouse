"""
OpenTelemetry Tracing — observability for agent operations.

Integrates with Phoenix (Arize) for distributed tracing.
Graceful degradation — if Phoenix is unreachable, tracing is a no-op.
"""

import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Try importing OpenTelemetry — optional dependency
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    _OTEL_AVAILABLE = True
except ImportError:
    _OTEL_AVAILABLE = False
    logger.debug("OpenTelemetry not installed. Tracing disabled.")


class Tracer:
    """
    Wrapper around OpenTelemetry with graceful fallback.

    Usage:
        tracer = Tracer(service_name="autofix-daemon")

        with tracer.span("diagnose_error") as span:
            span.set_attribute("error_type", "NullPointerException")
            # ... do work ...
            span.set_attribute("fix_applied", True)
    """

    def __init__(
        self,
        service_name: str = "powerhouse",
        phoenix_endpoint: str = "",
    ):
        self.service_name = service_name
        self.phoenix_endpoint = phoenix_endpoint or os.getenv(
            "PHOENIX_ENDPOINT", "http://localhost:6006/v1/traces"
        )
        self._tracer = None
        self._enabled = False
        self._init_tracer()

    def _init_tracer(self) -> None:
        """Initialize OpenTelemetry if available, otherwise no-op."""
        if not _OTEL_AVAILABLE:
            return

        try:
            provider = TracerProvider()
            exporter = OTLPSpanExporter(endpoint=self.phoenix_endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(self.service_name)
            self._enabled = True
            logger.info("Tracing enabled → %s", self.phoenix_endpoint)
        except Exception as e:
            logger.warning("Tracing init failed (no-op mode): %s", e)
            self._enabled = False

    @contextmanager
    def span(self, name: str, attributes: dict[str, Any] | None = None):
        """
        Context manager for a traced span.

        If tracing is disabled, this is a transparent no-op.
        """
        if not self._enabled or not self._tracer:
            # No-op span
            class _NoOpSpan:
                def set_attribute(self, key, value):
                    pass

                def add_event(self, name, attributes=None):
                    pass

                def set_status(self, status):
                    pass

            yield _NoOpSpan()
            return

        with self._tracer.start_as_current_span(name) as span:
            if attributes:
                for k, v in attributes.items():
                    span.set_attribute(k, str(v))
            yield span

    def log_event(
        self,
        event_name: str,
        service: str = "",
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Log a discrete event with structured attributes."""
        if not self._enabled:
            return

        with self.span(event_name) as span:
            span.set_attribute("service", service or self.service_name)
            span.set_attribute("timestamp", datetime.now(timezone.utc).isoformat())
            if attributes:
                for k, v in attributes.items():
                    span.set_attribute(k, str(v))

    @property
    def is_enabled(self) -> bool:
        return self._enabled


# Global singleton
_tracer: Tracer | None = None


def get_tracer(service_name: str = "powerhouse") -> Tracer:
    global _tracer
    if _tracer is None:
        _tracer = Tracer(service_name=service_name)
    return _tracer

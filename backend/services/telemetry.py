"""Opt-in API tracing; the standalone native/pyperf path does not import this module."""
from contextlib import nullcontext
from functools import wraps
import os

_tracer = None


def span(name, **attributes):
    if _tracer is None:
        return nullcontext()
    return _tracer.start_as_current_span(name, attributes=attributes)


def traced(name):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            with span(name):
                return function(*args, **kwargs)
        return wrapped
    return decorate


def configure_telemetry(app, *, exporter=None):
    global _tracer
    if os.getenv('NOVAQUANT_TELEMETRY_ENABLED', 'false').lower() != 'true':
        return None
    if getattr(app.state, 'telemetry_provider', None) is not None:
        return app.state.telemetry_provider
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    provider = TracerProvider(resource=Resource.create({
        'service.name': os.getenv('OTEL_SERVICE_NAME', 'novaquant-api')}))
    if exporter is None:
        exporter = OTLPSpanExporter(endpoint=os.getenv(
            'OTEL_EXPORTER_OTLP_TRACES_ENDPOINT', 'http://127.0.0.1:4318/v1/traces'), timeout=2)
    provider.add_span_processor(BatchSpanProcessor(exporter, schedule_delay_millis=1000))
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider, excluded_urls='/health',
                                     exclude_spans=['receive', 'send'])
    _tracer = provider.get_tracer('novaquant.research')
    app.state.telemetry_provider = provider
    return provider


def shutdown_telemetry(app):
    global _tracer
    provider = getattr(app.state, 'telemetry_provider', None)
    if provider is not None:
        provider.shutdown()
        app.state.telemetry_provider = None
        _tracer = None

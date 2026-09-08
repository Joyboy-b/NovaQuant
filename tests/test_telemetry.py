from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from backend.services import telemetry
from backend.api.backtest_api import backtest_router


def test_telemetry_disabled_by_default(monkeypatch):
    monkeypatch.delenv('NOVAQUANT_TELEMETRY_ENABLED', raising=False)
    monkeypatch.setattr(telemetry, '_tracer', None)
    app = FastAPI()
    assert telemetry.configure_telemetry(app) is None
    with telemetry.span('disabled'):
        pass
    assert not hasattr(app.state, 'telemetry_provider')


def test_request_trace_contains_compute_and_committed_database_spans(research, monkeypatch):
    monkeypatch.setenv('NOVAQUANT_TELEMETRY_ENABLED', 'true')
    monkeypatch.setattr(telemetry, '_tracer', None)
    app = FastAPI()
    app.include_router(backtest_router, prefix='/backtest')
    exporter = InMemorySpanExporter()
    provider = telemetry.configure_telemetry(app, exporter=exporter)
    assert telemetry.configure_telemetry(app, exporter=exporter) is provider
    try:
        with TestClient(app) as client:
            response = client.post('/backtest/run', json={'steps':100,'seed':42,'engine':'cpp'})
            assert response.status_code == 200
            assert client.get('/backtest/runs/'+response.json()['run_id']).status_code == 200
        assert provider.force_flush()
        spans = exporter.get_finished_spans()
        expected = {'backtest.data','backtest.engine','backtest.metrics','backtest.bootstrap',
                    'backtest.permutation','research.persist','research.transaction'}
        phases = {s.name:s for s in spans if s.name in expected}
        assert set(phases) == expected
        root = next(s for s in spans if s.name == 'POST /backtest/run')
        assert all(s.context.trace_id == root.context.trace_id for s in phases.values())
        assert phases['research.transaction'].parent.span_id == phases['research.persist'].context.span_id
        assert phases['backtest.engine'].attributes['engine'] == 'cpp'
        assert all(s.end_time >= s.start_time for s in spans)
    finally:
        telemetry.shutdown_telemetry(app)


def test_traced_exception_is_recorded(monkeypatch):
    monkeypatch.setenv('NOVAQUANT_TELEMETRY_ENABLED', 'true')
    monkeypatch.setattr(telemetry, '_tracer', None)
    app = FastAPI()
    exporter = InMemorySpanExporter()
    provider = telemetry.configure_telemetry(app, exporter=exporter)
    try:
        try:
            with telemetry.span('failed_operation'):
                raise ValueError('test failure')
        except ValueError:
            pass
        assert provider.force_flush()
        recorded = exporter.get_finished_spans()[0]
        assert recorded.status.status_code.name == 'ERROR'
        assert recorded.events[0].name == 'exception'
    finally:
        telemetry.shutdown_telemetry(app)

import os
from uuid import uuid4
import psycopg
from psycopg import sql
import pytest
from backend.services.research_store import ResearchStore


@pytest.fixture
def research(monkeypatch):
    dsn = os.getenv('TEST_DATABASE_URL')
    if not dsn:
        pytest.skip('TEST_DATABASE_URL required for PostgreSQL tests')
    schema = 'nova_test_'+uuid4().hex
    with psycopg.connect(dsn) as conn:
        conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    monkeypatch.setenv('DATABASE_SCHEMA',schema)
    store = ResearchStore(dsn)
    store.initialize()
    import backend.api.backtest_api as api
    monkeypatch.setattr(api,'get_research_store',lambda:store)
    try:
        yield store
    finally:
        store.close()
        with psycopg.connect(dsn) as conn:
            conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))

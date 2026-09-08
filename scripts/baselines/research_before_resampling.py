"""Durable research snapshots and results, isolated from live trading state."""
import hashlib
import json
import os
import threading
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from backend.services.telemetry import traced, span
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool


def dataset_identity(quotes):
    rows = [asdict(q) for q in quotes]
    canonical = json.dumps(rows, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(canonical.encode()).hexdigest(), rows


def engine_version():
    root = Path(__file__).resolve().parents[2]
    digest = hashlib.sha256()
    for path in sorted((root/'backend/backtest').rglob('*.py')) + sorted((root/'engine-cpp').glob('*.cpp')):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    for relative in ('backend/services/portfolio.py','backend/services/metrics.py','backend/api/backtest_api.py'):
        digest.update((root/relative).read_bytes())
    for path in sorted((root/'build-engine').glob('*novaquant_backtest*')):
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


class ResearchStore:
    def __init__(self, dsn=None):
        self.dsn = dsn or os.getenv('DATABASE_URL', 'postgresql://novaquant:novaquant@127.0.0.1:55433/novaquant')
        self.schema = os.getenv('DATABASE_SCHEMA', 'public')
        self.pool = ConnectionPool(self.dsn, min_size=1, max_size=8, open=False, timeout=5,
            kwargs={'row_factory':dict_row,'connect_timeout':5,'options':'-c statement_timeout=15000'},
            configure=self._configure)

    def _configure(self, conn):
        conn.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(self.schema)))
        conn.commit()

    def initialize(self):
        self.pool.open(wait=True, timeout=10)
        with self.pool.connection() as conn:
            conn.execute(Path(__file__).with_name('research_schema.sql').read_text())

    @traced('research.persist')
    def save(self, kind, config, quotes, response, elapsed_ms):
        dataset_id, rows = dataset_identity(quotes)
        run_id = uuid4()
        version = engine_version()
        result = {**response, 'run_id':str(run_id), 'dataset_id':dataset_id,
                  'engine_version':version, 'elapsed_ms':elapsed_ms}
        with span('research.transaction'):
            with self.pool.connection() as conn:
                conn.execute('INSERT INTO research_datasets(id,quotes) VALUES(%s,%s) ON CONFLICT(id) DO NOTHING',
                             (dataset_id, Jsonb(rows)))
                conn.execute('''INSERT INTO research_runs(id,kind,config,dataset_id,engine_version,result,elapsed_ms)
                    VALUES(%s,%s,%s,%s,%s,%s,%s)''',
                    (run_id,kind,Jsonb(config),dataset_id,version,Jsonb(result),elapsed_ms))
        return result

    def list(self, limit=50, offset=0):
        with self.pool.connection() as conn:
            return conn.execute('''SELECT id,kind,config,dataset_id,engine_version,elapsed_ms,created_at
                FROM research_runs ORDER BY created_at DESC,id DESC LIMIT %s OFFSET %s''', (limit,offset)).fetchall()

    def get(self, run_id):
        with self.pool.connection() as conn:
            return conn.execute('SELECT * FROM research_runs WHERE id=%s',(run_id,)).fetchone()

    def dataset(self, dataset_id):
        with self.pool.connection() as conn:
            return conn.execute('SELECT * FROM research_datasets WHERE id=%s',(dataset_id,)).fetchone()

    def close(self):
        self.pool.close()


_instance = None
_lock = threading.Lock()


def get_research_store():
    global _instance
    with _lock:
        if _instance is None:
            candidate = ResearchStore()
            try:
                candidate.initialize()
            except Exception:
                candidate.close()
                raise
            _instance = candidate
        return _instance


def close_research_store():
    global _instance
    with _lock:
        if _instance:
            _instance.close()
            _instance = None

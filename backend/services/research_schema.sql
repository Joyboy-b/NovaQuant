CREATE TABLE IF NOT EXISTS research_datasets (
    id text PRIMARY KEY CHECK(length(id)=64),
    quotes jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS research_runs (
    id uuid PRIMARY KEY,
    kind text NOT NULL CHECK(kind IN ('backtest','walkforward','sweep')),
    config jsonb NOT NULL,
    dataset_id text NOT NULL REFERENCES research_datasets(id),
    engine_version text NOT NULL,
    result jsonb NOT NULL,
    elapsed_ms double precision NOT NULL CHECK(elapsed_ms>=0),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS research_runs_recent ON research_runs(created_at DESC,id DESC);

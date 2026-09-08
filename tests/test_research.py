from uuid import UUID
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.api.backtest_api import backtest_router


def test_run_persists_snapshot_trades_equity_and_replays_on_cpp(research):
    app=FastAPI();app.include_router(backtest_router,prefix='/backtest')
    with TestClient(app) as client:
        response=client.post('/backtest/run',json={'steps':100,'seed':42})
        assert response.status_code==200,response.text
        first=response.json()
    # A fresh client can retrieve the committed result.
    with TestClient(app) as client:
        saved=client.get('/backtest/runs/'+first['run_id']).json()
        assert saved['result']['equity']==first['equity']
        assert saved['result']['trades']==first['trades']
        snapshot=client.get('/backtest/datasets/'+first['dataset_id']).json()
        assert len(snapshot['quotes'])==100
        replay=client.post('/backtest/run',json={'dataset_id':first['dataset_id'],'engine':'cpp'}).json()
        assert replay['dataset_id']==first['dataset_id']
        import pytest
        assert replay['equity']==pytest.approx(first['equity'])
        assert len(client.get('/backtest/runs').json())==2
    with research.pool.connection() as conn:
        assert conn.execute('SELECT count(*) AS n FROM research_datasets').fetchone()['n']==1


def test_walkforward_and_sweep_saved(research):
    app=FastAPI();app.include_router(backtest_router,prefix='/backtest')
    with TestClient(app) as client:
        wf=client.post('/backtest/walkforward',json={'steps':100,'train_size':50,'test_size':25,'seed':1})
        assert wf.status_code==200,wf.text
        assert research.get(UUID(wf.json()['run_id']))['kind']=='walkforward'
        sweep=client.post('/backtest/sweep',json={'steps':50,'seed':1,'lookbacks':[5],
            'fee_bps_list':[0,2],'slippage_bps_list':[0]})
        assert sweep.status_code==200,sweep.text
        assert len(sweep.json()['top_details'])==2
        assert research.get(UUID(sweep.json()['run_id']))['kind']=='sweep'


def test_research_transactions_rollback_together(research):
    from backend.backtest.data import quotes_from_mid_prices
    import pytest
    import psycopg
    with pytest.raises(psycopg.errors.CheckViolation):
        research.save('invalid',{},quotes_from_mid_prices([100,101]),{},1)
    with research.pool.connection() as conn:
        assert conn.execute('SELECT count(*) AS n FROM research_datasets').fetchone()['n']==0

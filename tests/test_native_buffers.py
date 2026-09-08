"""Buffer lifetime, empty inputs, validation and same-kernel output equivalence."""
from concurrent.futures import ThreadPoolExecutor
import pytest
from backend.backtest import native
from backend.backtest.data import Quote, quotes_from_mid_prices
from scripts.baselines import native_before_buffers as baseline


@pytest.mark.parametrize('prices,lookback', [([],10),([100],10),([100]*30,10),([100,101,99,103,97]*20,2)])
def test_buffer_adapter_matches_original(prices,lookback,monkeypatch):
    monkeypatch.setattr(baseline,'library',native.library)
    quotes=quotes_from_mid_prices(prices)
    assert native.run_native(quotes,'X',lookback,2.5,5,3)==baseline.run_native(quotes,'X',lookback,2.5,5,3)


def test_buffers_are_isolated_across_concurrent_calls():
    def run(seed):
        quotes=quotes_from_mid_prices([100+(i+seed)%7 for i in range(500)])
        return native.run_native(quotes,'X',3,1,1,2)
    expected=[run(i) for i in range(12)]
    with ThreadPoolExecutor(4) as pool:
        assert list(pool.map(run,range(12)))==expected


@pytest.mark.parametrize('quote', [Quote(0,float('nan'),99,101), Quote(0,100,101,99)])
def test_buffer_adapter_preserves_native_validation(quote):
    with pytest.raises(ValueError,match='code 2'):
        native.run_native([quote],'X',10,1,1,2)

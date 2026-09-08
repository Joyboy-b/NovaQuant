import numpy as np
import pytest
from backend.backtest import stats
from scripts.baselines import stats_before_resampling as baseline

@pytest.mark.parametrize('seed',[0,1,42])
@pytest.mark.parametrize('size',[0,1,7,100])
@pytest.mark.parametrize('n',[1,31,33])
def test_seeded_resampling_matches_original_exactly(seed,size,n):
    values = np.random.default_rng(seed).normal(size=size).tolist()
    assert stats.bootstrap_mean_ci(values,n=n,seed=seed)==baseline.bootstrap_mean_ci(values,n=n,seed=seed)
    assert stats.permutation_test_mean_gt_zero(values,n=n,seed=seed)==baseline.permutation_test_mean_gt_zero(values,n=n,seed=seed)

def test_zero_series_and_single_observation():
    assert stats.bootstrap_mean_ci([3.0],seed=42)=={'mean':3.0,'lo':3.0,'hi':3.0}
    assert stats.permutation_test_mean_gt_zero([0.0]*17,seed=42)=={'mean':0.0,'p_value':1.0}
    expected = float((np.random.default_rng(42).integers(0,2,size=100)==1).mean())
    assert stats.permutation_test_mean_gt_zero([1.0],n=100,seed=42)['p_value']==expected

@pytest.mark.parametrize('function',[stats.bootstrap_mean_ci,stats.permutation_test_mean_gt_zero])
def test_nonpositive_trials_rejected(function):
    with pytest.raises(ValueError):function([1.0],n=0)

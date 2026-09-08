"""Dedicated old/new statistics comparison; both use the current optimized adapter."""
import hashlib
import os
from pathlib import Path
from backend.api import backtest_api
from backend.backtest import stats
from backend.services import research_store
from scripts.baselines import stats_before_resampling as baseline
variant=os.environ['NOVAQUANT_COMPARISON_ADAPTER']
if variant=='before':
    backtest_api.bootstrap_mean_ci=baseline.bootstrap_mean_ci
    backtest_api.permutation_test_mean_gt_zero=baseline.permutation_test_mean_gt_zero
elif variant!='after':raise ValueError('Expected before or after')
original_version=research_store.engine_version
source=Path(baseline.__file__ if variant=='before' else stats.__file__)
def version():return hashlib.sha256(original_version().encode()+variant.encode()+source.read_bytes()).hexdigest()
research_store.engine_version=version
from backend.api.app import app

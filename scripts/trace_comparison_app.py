"""Dedicated comparison entry point; never changes the normal API's adapter."""
import os
from backend.api import backtest_api
from backend.backtest import native
from scripts.baselines import native_before_buffers

variant = os.environ['NOVAQUANT_COMPARISON_ADAPTER']
if variant == 'before':
    native_before_buffers.library = native.library
    backtest_api.run_native = native_before_buffers.run_native
elif variant != 'after':
    raise ValueError('Expected before or after adapter')
# Include the actual comparison adapter in persisted implementation provenance.
import hashlib
from pathlib import Path
from backend.services import research_store
original_version = research_store.engine_version
adapter_path = Path(native_before_buffers.__file__ if variant == 'before' else native.__file__)
def comparison_version():
    return hashlib.sha256(original_version().encode() + variant.encode() + adapter_path.read_bytes()).hexdigest()
research_store.engine_version = comparison_version
from backend.api.app import app

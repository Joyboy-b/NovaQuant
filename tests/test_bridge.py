import asyncio
from pathlib import Path
import sys
import pytest
from backend.api.async_engine_bridge import EngineBridge


def test_concurrent_orders_correlate_out_of_order_and_do_not_block_loop():
    async def scenario():
        fills=[]
        bridge=EngineBridge(sys.executable,args=[str(Path(__file__).with_name('fake_engine.py'))],on_fill=fills.extend)
        await bridge.start()
        try:
            slow=asyncio.create_task(bridge.execute({'order_id':'slow','delay':.2}))
            fast=asyncio.create_task(bridge.execute({'order_id':'fast','delay':.01}))
            result=await fast
            assert all(r['order_id']=='fast' for r in result)
            assert not slow.done()
            assert all(r['order_id']=='slow' for r in await slow)
            assert [r['order_id'] for r in fills]==['fast','slow']
            with pytest.raises(ValueError):
                await bridge.execute({'order_id':'fast'})
        finally:await bridge.stop()
    asyncio.run(scenario())


def test_late_fill_applied_once_after_timeout():
    async def scenario():
        fills=[]
        bridge=EngineBridge(sys.executable,args=[str(Path(__file__).with_name('fake_engine.py'))],on_fill=fills.extend)
        await bridge.start()
        try:
            with pytest.raises(TimeoutError):
                await bridge.execute({'order_id':'late','delay':.1},timeout=.01)
            await asyncio.sleep(.3)
            assert len(fills)==1
            assert not bridge.pending
        finally:await bridge.stop()
    asyncio.run(scenario())

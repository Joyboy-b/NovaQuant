"""Async NDJSON transport with per-order completion, not quiet-period polling."""
import asyncio
import json
import logging
from backend.api.engine_bridge import default_engine_path

logger = logging.getLogger(__name__)


class EngineBridge:
    def __init__(self, exe_path: str, *, args=(), on_fill=None):
        self.exe_path, self.args, self.on_fill = exe_path, args, on_fill
        self.proc = None
        self.pending = {}
        self.seen = set()
        self.filled = set()
        self.tasks = []
        self.write_lock = asyncio.Lock()

    async def start(self):
        self.proc = await asyncio.create_subprocess_exec(
            self.exe_path, *self.args, stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        self.tasks = [asyncio.create_task(self._read()), asyncio.create_task(self._stderr())]

    def is_alive(self):
        return self.proc is not None and self.proc.returncode is None

    async def _stderr(self):
        while line := await self.proc.stderr.readline():
            logger.warning('engine stderr: %s', line.decode(errors='replace').rstrip())

    async def _read(self):
        try:
            while line := await self.proc.stdout.readline():
                report = json.loads(line)
                order_id = report.get('order_id')
                entry = self.pending.get(order_id)
                if report.get('type') == 'fill' and order_id in self.seen and order_id not in self.filled:
                    # A client timeout does not cancel an executed order; apply late fills.
                    if self.on_fill:
                        self.on_fill([report])
                    self.filled.add(order_id)
                if entry:
                    future, reports = entry
                    reports.append(report)
                    if report.get('type') in {'fill', 'error', 'reject'} and not future.done():
                        future.set_result(reports)
        except Exception:
            logger.exception('Engine report reader failed')
        finally:
            for future, _ in self.pending.values():
                if not future.done():
                    future.set_exception(ConnectionError('Engine report stream closed'))

    async def execute(self, message, timeout=2.0):
        if not self.is_alive() or any(t.done() for t in self.tasks):
            raise ConnectionError('Engine unavailable')
        order_id = message['order_id']
        if order_id in self.seen:
            raise ValueError('Order ID already used in this session')
        if len(self.seen) >= 100000:
            raise ValueError('Session order limit reached; start a new session')
        future = asyncio.get_running_loop().create_future()
        self.seen.add(order_id)
        self.pending[order_id] = (future, [])
        try:
            async with asyncio.timeout(timeout):
                async with self.write_lock:
                    self.proc.stdin.write((json.dumps(message)+'\n').encode())
                    await self.proc.stdin.drain()
                return await future
        finally:
            self.pending.pop(order_id, None)

    async def stop(self):
        if self.is_alive():
            self.proc.terminate()
            try:
                await asyncio.wait_for(self.proc.wait(), 5)
            except asyncio.TimeoutError:
                self.proc.kill()
                await self.proc.wait()
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)

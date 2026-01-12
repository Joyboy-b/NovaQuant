# backend/api/engine_bridge.py
from __future__ import annotations

import json
import queue
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class EngineBridge:
    """
    Minimal newline-delimited JSON (NDJSON) bridge over stdin/stdout.

    Engine contract:
      - Python writes one JSON object per line to stdin
      - Engine writes one JSON object per line to stdout
    """

    def __init__(self, exe_path: str):
        self.exe_path = exe_path
        self.proc: Optional[subprocess.Popen] = None
        self._out_q: "queue.Queue[str]" = queue.Queue()
        self._err_q: "queue.Queue[str]" = queue.Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self._err_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self.is_alive():
            return

        self.proc = subprocess.Popen(
            [self.exe_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        assert self.proc.stdout is not None
        assert self.proc.stderr is not None

        def _reader():
            for line in self.proc.stdout:
                self._out_q.put(line.rstrip("\n"))

        def _err_reader():
            for line in self.proc.stderr:
                self._err_q.put(line.rstrip("\n"))

        self._reader_thread = threading.Thread(target=_reader, daemon=True)
        self._err_thread = threading.Thread(target=_err_reader, daemon=True)
        self._reader_thread.start()
        self._err_thread.start()

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

    def is_alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def send(self, message: Dict[str, Any]) -> None:
        if not self.is_alive() or self.proc is None or self.proc.stdin is None:
            raise RuntimeError("Engine not running")

        payload = json.dumps(message) + "\n"
        self.proc.stdin.write(payload)
        self.proc.stdin.flush()

    def recv_all(self, timeout: Optional[float] = 2.0) -> List[Dict[str, Any]]:
        """
        Drain stdout queue for up to `timeout` seconds (best-effort).
        Returns list of decoded JSON objects; ignores malformed lines.
        """
        messages: List[Dict[str, Any]] = []
        deadline = time.time() + (timeout if timeout is not None else 10**9)

        while time.time() < deadline:
            try:
                line = self._out_q.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                # keep going; engine might emit logs
                continue

        return messages

    def stderr_drain(self, max_lines: int = 200) -> List[str]:
        """
        Optional helper: grab engine stderr lines for debugging.
        """
        lines: List[str] = []
        for _ in range(max_lines):
            try:
                lines.append(self._err_q.get_nowait())
            except queue.Empty:
                break
        return lines


def default_engine_path() -> str:
    root = Path(__file__).resolve().parents[2]  # repo root
    candidates = [
        root / "build-engine" / "Release" / "novaquant_engine.exe",
        root / "build-engine" / "novaquant_engine.exe",
        root / "build-engine" / "novaquant_engine",  # linux/mac
    ]
    for cand in candidates:
        if cand.exists():
            return str(cand)
    raise FileNotFoundError("novaquant_engine executable not found in build-engine/")

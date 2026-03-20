from __future__ import annotations

import threading
from pathlib import Path

from ptyprocess import PtyProcess


class TerminalService:
    def __init__(self) -> None:
        self._sessions: dict[str, PtyProcess] = {}
        self._lock = threading.Lock()

    def create_session(self, session_id: str, cwd: Path) -> PtyProcess:
        with self._lock:
            existing = self._sessions.get(session_id)
            if existing and existing.isalive():
                return existing

            process = PtyProcess.spawn(["/bin/bash"], cwd=str(cwd))
            self._sessions[session_id] = process
            return process

    def write(self, session_id: str, data: str) -> None:
        process = self._sessions.get(session_id)
        if process and process.isalive():
            process.write(data.encode("utf-8"))

    def read_nonblocking(self, session_id: str, size: int = 4096) -> str:
        process = self._sessions.get(session_id)
        if not process or not process.isalive():
            return ""
        try:
            data = process.read_nonblocking(size=size, timeout=0)
        except Exception:
            return ""
        return data.decode("utf-8", errors="ignore")

    def close_session(self, session_id: str) -> None:
        with self._lock:
            process = self._sessions.pop(session_id, None)
            if process and process.isalive():
                process.terminate(force=True)


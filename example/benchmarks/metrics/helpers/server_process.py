"""
Shared dev-server subprocess management for collectors that need real
HTTP (payload, client) rather than the in-process Django test client
(static, server). Used as a context manager:

    with DevServer(PORT) as server:
        requests.get(f"{server.base_url}/...")
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import requests

# .../example/benchmarks/metrics/server_process.py -> parents[2] = .../example
MANAGE_PY = Path(__file__).resolve().parents[2] / "manage.py"


class DevServer:
    def __init__(self, port: int):
        self.port = port
        self.base_url = f"http://127.0.0.1:{port}"
        self._proc: subprocess.Popen | None = None

    def __enter__(self) -> "DevServer":
        env = os.environ.copy()
        # Disables the debug-swap marker script and switches to vendored
        # local htmx/idiomorph assets if present (see vendor_client_assets).
        env.setdefault("HTMX_NAV_BENCHMARK", "1")
        self._proc = subprocess.Popen(
            [
                sys.executable,
                str(MANAGE_PY),
                "runserver",
                f"127.0.0.1:{self.port}",
                "--noreload",
            ],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._wait_ready()
        return self

    def __exit__(self, *exc_info) -> None:
        self._proc.terminate()
        try:
            self._proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self._proc.kill()

    def _wait_ready(self, timeout: int = 15) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                requests.get(self.base_url, timeout=1)
                return
            except requests.exceptions.ConnectionError:
                time.sleep(0.3)
        raise RuntimeError(f"Dev server on port {self.port} did not start in time.")

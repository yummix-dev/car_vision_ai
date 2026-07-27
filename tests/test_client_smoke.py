"""Executes the client render code and fails on any thrown error.

The Python suite never runs the SPA's JavaScript, so a render-time bug —
a variable renamed on one line but not another (`STEP_LABELS`), a screen using
`t()` without importing it — ships green and breaks the funnel only in a browser.
`smoke_client.mjs` renders every screen under Node with browser shims; this test
runs it and surfaces its output. It skips where Node is unavailable rather than
failing the suite on a machine without it.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

SMOKE = Path(__file__).parent / "smoke_client.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_client_screens_render_without_errors():
    result = subprocess.run(
        ["node", str(SMOKE)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert result.returncode == 0, (
        "client render smoke failed:\n"
        f"{result.stdout}\n{result.stderr}"
    )

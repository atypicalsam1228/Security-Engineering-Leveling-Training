from __future__ import annotations

import sys

import pytest

from labcli.executor import RunResult, SubprocessRunner


def test_runs_and_captures() -> None:
    result = SubprocessRunner().run((sys.executable, "-c", "print('hi')"))
    assert result.returncode == 0 and result.output.strip() == "hi"


def test_nonzero_exit() -> None:
    assert SubprocessRunner().run((sys.executable, "-c", "import sys; sys.exit(3)")).returncode == 3


def test_timeout_reported() -> None:
    result = SubprocessRunner().run((sys.executable, "-c", "import time; time.sleep(5)"), timeout=0.2)
    assert result.returncode != 0 and "timed out" in result.output


def test_missing_binary_raises() -> None:
    with pytest.raises(OSError):
        SubprocessRunner().run(("definitely-not-a-binary-xyz",))


def test_interactive_returns_code() -> None:
    assert SubprocessRunner().run_interactive((sys.executable, "-c", "pass")) == 0


def test_runresult_is_frozen() -> None:
    with pytest.raises(AttributeError):
        RunResult(0, "").returncode = 1  # type: ignore[misc]

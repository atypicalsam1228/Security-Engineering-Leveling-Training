"""Process execution behind a small interface so tests can mock it."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Protocol

DEFAULT_TIMEOUT_SECONDS = 600.0


@dataclass(frozen=True)
class RunResult:
    returncode: int
    output: str


class Runner(Protocol):
    def run(self, argv: tuple[str, ...], timeout: float | None = None) -> RunResult: ...

    def run_interactive(self, argv: tuple[str, ...]) -> int: ...


class SubprocessRunner:
    """Real runner. Captures combined stdout and stderr as text."""

    def run(self, argv: tuple[str, ...], timeout: float | None = DEFAULT_TIMEOUT_SECONDS) -> RunResult:
        try:
            done = subprocess.run(
                list(argv),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return RunResult(124, f"timed out after {timeout} seconds")
        return RunResult(done.returncode, (done.stdout or "") + (done.stderr or ""))

    def run_interactive(self, argv: tuple[str, ...]) -> int:
        return subprocess.run(list(argv), check=False).returncode

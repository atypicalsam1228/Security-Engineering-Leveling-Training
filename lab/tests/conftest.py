"""Shared fixtures: a tiny fake generators tree and a recording runner."""
from __future__ import annotations

from pathlib import Path

import pytest

from labcli.executor import RunResult

MODULE_TEMPLATE = r'''
MODULE = {{
    "id": "{id}",
    "title": "Title {id}",
    "prereq": ["Module 0 (terminal and git basics)"],
    "minutes": {{"hands_on": 40, "verify": 15}},
    "lab": {{"start": "lab start {low}", "env": ["LOKI_URL", "LOKI_PASSWORD"]}},
    "lab_needs": ["need one"],
    "verify": [
        {{"kind": "positive", "title": "ok test", "code": "echo hello", "expect": "hello"}},
        {{"kind": "negative", "title": "loose test", "code": "echo x", "expect": "Example only.\nlabel: value"}},
    ],
}}
'''


@pytest.fixture()
def gen_dir(tmp_path: Path) -> Path:
    root = tmp_path / "generators"
    (root / "content").mkdir(parents=True)
    (root / "order.py").write_text('TRACK = ["ENG-0", "GRC-2"]\n', encoding="utf-8")
    for module_id in ("ENG-0", "GRC-2"):
        low = module_id.lower()
        name = low.replace("-", "_")
        (root / "content" / f"{name}.py").write_text(
            MODULE_TEMPLATE.format(id=module_id, low=low), encoding="utf-8"
        )
    return root


class FakeRunner:
    """Records commands; returns canned results keyed by a substring of the argv."""

    def __init__(self, results: dict[str, RunResult] | None = None) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.results = results or {}

    def run(self, argv: tuple[str, ...], timeout: float | None = None) -> RunResult:
        self.calls.append(tuple(argv))
        joined = " ".join(argv)
        for key, result in self.results.items():
            if key in joined:
                return result
        return RunResult(0, "")

    def run_interactive(self, argv: tuple[str, ...]) -> int:
        return self.run(argv).returncode

from __future__ import annotations

import io
from pathlib import Path

from labcli.catalog import load_catalog
from labcli.cli import Deps, main

from conftest import FakeRunner

MODULE = r'''
MODULE = {
    "id": "%s",
    "title": "Title %s",
    "prereq": [],
    "minutes": {"hands_on": 40, "verify": 15},
    "lab": {"start": "lab start x", "env": []},
    %s
}
'''


def build(tmp_path: Path):
    gen = tmp_path / "generators"
    (gen / "content").mkdir(parents=True)
    (gen / "order.py").write_text('TRACK = ["ENG-0", "ARC-5"]\n', encoding="utf-8")
    (gen / "content" / "eng_0.py").write_text(MODULE % ("ENG-0", "ENG-0", ""), encoding="utf-8")
    (gen / "content" / "arc_5.py").write_text(MODULE % ("ARC-5", "ARC-5", '"optional": True,'), encoding="utf-8")
    out = io.StringIO()
    deps = Deps(runner=FakeRunner(), out=out, ask=lambda p: "", which=lambda n: f"/bin/{n}",
                environ={"LAB_WORKSPACE": str(tmp_path / "ws"), "LAB_GENERATORS_DIR": str(gen)})
    return gen, deps, out


def test_catalog_reads_optional_flag(tmp_path) -> None:
    gen, _, _ = build(tmp_path)
    modules = load_catalog(gen).modules
    assert [m.optional for m in modules] == [False, True]


def test_modules_listing_marks_optional(tmp_path) -> None:
    _, deps, out = build(tmp_path)
    assert main(["modules"], deps) == 0
    lines = out.getvalue().splitlines()
    assert any("ARC-5" in l and "(optional)" in l for l in lines)
    assert not any("ENG-0" in l and "(optional)" in l for l in lines)

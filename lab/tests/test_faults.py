from __future__ import annotations

import io
import json
from pathlib import Path

from conftest import FakeRunner
from labcli.cli import Deps, main
from labcli.executor import RunResult

FAULT_MODULE = r'''
MODULE = {
    "id": "GRC-2",
    "title": "Title GRC-2",
    "prereq": [],
    "minutes": {"hands_on": 40, "verify": 15},
    "lab": {"start": "lab start grc-2", "env": []},
    "verify": [{"kind": "positive", "title": "ok", "code": "echo hello", "expect": "hello"}],
    "faults": [
        {"id": "alpha", "title": "Alpha fault", "break_code": "echo break-alpha", "restore_code": "echo restore-alpha"},
        {"id": "beta", "title": "Beta fault", "break_code": "echo break-beta", "restore_code": "echo restore-beta"},
    ],
}
'''

NO_FAULT_MODULE = FAULT_MODULE.replace('"id": "GRC-2"', '"id": "ENG-0"').split('"faults"')[0] + "}\n"


def build(tmp_path: Path, runner, in_shell: bool = True):
    gen = tmp_path / "generators"
    (gen / "content").mkdir(parents=True)
    (gen / "order.py").write_text('TRACK = ["ENG-0", "GRC-2"]\n', encoding="utf-8")
    (gen / "content" / "grc_2.py").write_text(FAULT_MODULE, encoding="utf-8")
    (gen / "content" / "eng_0.py").write_text(NO_FAULT_MODULE, encoding="utf-8")
    out = io.StringIO()
    environ = {"LAB_WORKSPACE": str(tmp_path / "ws"), "LAB_GENERATORS_DIR": str(gen), "LAB_IN_SHELL": "1" if in_shell else ""}
    deps = Deps(runner=runner, out=out, ask=lambda p: "", which=lambda n: f"/bin/{n}", environ=environ)
    return deps, out


def ran(runner: FakeRunner, text: str) -> bool:
    return any(text in " ".join(call) for call in runner.calls)


def test_list_shows_faults_and_none_active(tmp_path) -> None:
    deps, out = build(tmp_path, FakeRunner())
    assert main(["break", "grc-2", "--list"], deps) == 0
    text = out.getvalue()
    assert "alpha" in text and "beta" in text and "active" not in text.lower()


def test_break_one_runs_only_that_fault(tmp_path) -> None:
    runner = FakeRunner()
    deps, out = build(tmp_path, runner)
    assert main(["break", "grc-2", "alpha"], deps) == 0
    assert ran(runner, "break-alpha") and not ran(runner, "break-beta")
    assert "alpha" in out.getvalue()


def test_break_all_runs_every_fault(tmp_path) -> None:
    runner = FakeRunner()
    deps, _ = build(tmp_path, runner)
    assert main(["break", "grc-2", "--all"], deps) == 0
    assert ran(runner, "break-alpha") and ran(runner, "break-beta")


def test_list_marks_active_after_break(tmp_path) -> None:
    deps, out = build(tmp_path, FakeRunner())
    main(["break", "grc-2", "beta"], deps)
    main(["break", "grc-2", "--list"], deps)
    lines = [l for l in out.getvalue().splitlines() if "beta" in l and "ACTIVE" in l]
    assert lines
    assert not [l for l in out.getvalue().splitlines() if "alpha" in l and "ACTIVE" in l]


def test_restore_one_clears_active(tmp_path) -> None:
    runner = FakeRunner()
    deps, out = build(tmp_path, runner)
    main(["break", "grc-2", "--all"], deps)
    assert main(["restore", "grc-2", "alpha"], deps) == 0
    assert ran(runner, "restore-alpha") and not ran(runner, "restore-beta")
    record = json.loads((tmp_path / "ws" / ".lab" / "faults.json").read_text(encoding="utf-8"))
    assert record["GRC-2"] == ["beta"]


def test_restore_all_runs_every_restore_even_if_not_recorded(tmp_path) -> None:
    runner = FakeRunner()
    deps, _ = build(tmp_path, runner)
    assert main(["restore", "grc-2", "--all"], deps) == 0
    assert ran(runner, "restore-alpha") and ran(runner, "restore-beta")


def test_failed_break_is_not_recorded_and_fails(tmp_path) -> None:
    runner = FakeRunner({"break-alpha": RunResult(1, "no labels matched")})
    deps, out = build(tmp_path, runner)
    assert main(["break", "grc-2", "alpha"], deps) == 1
    assert "no labels matched" in out.getvalue()
    assert not (tmp_path / "ws" / ".lab" / "faults.json").exists()


def test_unknown_fault_lists_choices(tmp_path) -> None:
    runner = FakeRunner()
    deps, out = build(tmp_path, runner)
    assert main(["break", "grc-2", "nope"], deps) == 2
    assert runner.calls == [] and "alpha" in out.getvalue()


def test_module_without_faults_is_reported(tmp_path) -> None:
    deps, out = build(tmp_path, FakeRunner())
    assert main(["break", "eng-0", "--list"], deps) == 2
    assert "no faults" in out.getvalue().lower()


def test_needs_fault_or_flag(tmp_path) -> None:
    deps, out = build(tmp_path, FakeRunner())
    assert main(["break", "grc-2"], deps) == 2
    assert "--all" in out.getvalue()


def test_dry_run_runs_nothing_and_records_nothing(tmp_path) -> None:
    runner = FakeRunner()
    deps, out = build(tmp_path, runner)
    assert main(["break", "grc-2", "alpha", "--dry-run"], deps) == 0
    assert runner.calls == [] and "break-alpha" in out.getvalue()
    assert not (tmp_path / "ws" / ".lab" / "faults.json").exists()


def test_fault_text_is_redacted(tmp_path) -> None:
    runner = FakeRunner({"break-alpha": RunResult(1, "password=s3cretvalue")})
    deps, out = build(tmp_path, runner)
    deps.environ["LOKI_PASSWORD"] = "s3cretvalue"
    main(["break", "grc-2", "alpha"], deps)
    assert "s3cretvalue" not in out.getvalue()


def test_status_lists_active_faults(tmp_path) -> None:
    deps, out = build(tmp_path, FakeRunner())
    main(["status"], deps)
    assert "Faults active: none" in out.getvalue()
    main(["break", "grc-2", "alpha"], deps)
    main(["status"], deps)
    assert "Faults active: GRC-2 (alpha)" in out.getvalue()


def test_start_warns_when_a_fault_is_still_active(tmp_path) -> None:
    runner = FakeRunner()
    deps, out = build(tmp_path, runner)
    (tmp_path / "states" / "eng-0").mkdir(parents=True)
    (tmp_path / "states" / "eng-0" / "10-ns.yaml").write_text("kind: Namespace", encoding="utf-8")
    deps.environ["LAB_STATES_DIR"] = str(tmp_path / "states")
    main(["break", "grc-2", "alpha"], deps)
    main(["start", "eng-0"], deps)
    text = out.getvalue()
    assert "still active" in text and "lab restore grc-2 --all" in text


def test_start_is_silent_when_no_fault_is_active(tmp_path) -> None:
    deps, out = build(tmp_path, FakeRunner())
    (tmp_path / "states" / "eng-0").mkdir(parents=True)
    (tmp_path / "states" / "eng-0" / "10-ns.yaml").write_text("kind: Namespace", encoding="utf-8")
    deps.environ["LAB_STATES_DIR"] = str(tmp_path / "states")
    main(["start", "eng-0"], deps)
    assert "still active" not in out.getvalue()

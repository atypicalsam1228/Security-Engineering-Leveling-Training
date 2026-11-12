from __future__ import annotations

import io
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from conftest import FakeRunner
from labcli.cli import Deps, main
from labcli.environment import CONTRACT_VARS
from labcli.executor import RunResult
from labcli.guard import Heartbeat, pause_estimate

NOW = datetime(2026, 10, 30, 12, 0, 0, tzinfo=timezone.utc)
BUCKET = "guard-bucket-1"
LAB = "lab-abc"


class Clock:
    def __init__(self) -> None:
        self.now = NOW
        self.sleeps: list[float] = []

    def __call__(self) -> datetime:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += timedelta(seconds=seconds)


def deps_for(tmp_path: Path, gen_dir: Path, runner, guard: bool = True, lab: bool = True,
             in_shell: bool = False, clock: Clock | None = None):
    clock = clock or Clock()
    out = io.StringIO()
    environ = {"LAB_WORKSPACE": str(tmp_path / "ws"), "LAB_GENERATORS_DIR": str(gen_dir),
               "LOKI_PASSWORD": "s3cretvalue", "HOME": str(tmp_path)}
    if guard:
        environ["GUARD_BUCKET"] = BUCKET
    if lab:
        environ["LAB_ID"] = LAB
    if in_shell:
        environ["LAB_IN_SHELL"] = "1"
    deps = Deps(runner, out, lambda p: "", lambda n: f"/bin/{n}", environ, now=clock, sleep=clock.sleep)
    return deps, out, clock


def put_calls(runner: FakeRunner) -> list[tuple[str, ...]]:
    return [c for c in runner.calls if "put-object" in c]


def test_guard_bucket_is_a_contract_var() -> None:
    assert "GUARD_BUCKET" in CONTRACT_VARS


@pytest.mark.parametrize("cmd", ["keep", "pause", "resume", "pull"])
def test_missing_guard_bucket(cmd, tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, out, _ = deps_for(tmp_path, gen_dir, runner, guard=False)
    assert main([cmd], deps) == 2
    assert "GUARD_BUCKET" in out.getvalue() and "lab down" in out.getvalue()
    assert runner.calls == []


@pytest.mark.parametrize("cmd", ["keep", "pause", "resume", "pull"])
def test_missing_lab_id(cmd, tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, out, _ = deps_for(tmp_path, gen_dir, runner, lab=False)
    assert main([cmd], deps) == 2
    assert "LAB_ID" in out.getvalue() and "lab down" in out.getvalue()
    assert runner.calls == []


@pytest.mark.parametrize("cmd", ["keep", "pause", "resume", "pull"])
def test_refused_inside_shell(cmd, tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, out, _ = deps_for(tmp_path, gen_dir, runner, in_shell=True)
    assert main([cmd], deps) == 2
    assert "own computer" in out.getvalue() and runner.calls == []


def test_invalid_lab_id_rejected(tmp_path, gen_dir) -> None:
    deps, out, _ = deps_for(tmp_path, gen_dir, FakeRunner())
    bad = Deps(deps.runner, deps.out, deps.ask, deps.which, {**deps.environ, "LAB_ID": "../x"})
    assert main(["keep"], bad) == 2 and "not valid" in out.getvalue()


def test_settings_fall_back_to_lab_env_file(tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, _, _ = deps_for(tmp_path, gen_dir, runner, guard=False, lab=False)
    env_file = tmp_path / "ws" / ".lab" / "lab.env"
    env_file.parent.mkdir(parents=True)
    env_file.write_text(f"GUARD_BUCKET={BUCKET}\nLAB_ID={LAB}\n", encoding="utf-8")
    assert main(["keep"], deps) == 0
    assert f"heartbeat" not in " ".join(put_calls(runner)[0])
    assert f"keep/{LAB}" in put_calls(runner)[0]


def test_keep_default_four_hours(tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, out, _ = deps_for(tmp_path, gen_dir, runner)
    assert main(["keep"], deps) == 0
    call = put_calls(runner)[0]
    assert call[call.index("--key") + 1] == f"keep/{LAB}"
    body = tmp_path / "ws" / ".lab" / f"guard-keep-{LAB}"
    assert json.loads(body.read_text(encoding="utf-8")) == {"until": "2026-10-30T16:00:00Z"}
    assert "\r" not in body.read_text(encoding="utf-8")
    assert "lab down" in out.getvalue()
    assert any(a.endswith(":/workspace") for a in call)  # ran in the tools container
    assert call[call.index("--body") + 1] == f"/workspace/.lab/guard-keep-{LAB}"


def test_keep_explicit_hours_and_no_secrets_on_command_line(tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, _, _ = deps_for(tmp_path, gen_dir, runner)
    assert main(["keep", "24"], deps) == 0
    assert "2026-10-31T12:00:00Z" in (tmp_path / "ws" / ".lab" / f"guard-keep-{LAB}").read_text(encoding="utf-8")
    assert "s3cretvalue" not in " ".join(runner.calls[0])


@pytest.mark.parametrize("hours", ["0", "25", "-3"])
def test_keep_hours_out_of_range(hours, tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, out, _ = deps_for(tmp_path, gen_dir, runner)
    assert main(["keep", hours], deps) == 2
    assert "1 to 24" in out.getvalue() and runner.calls == []


def test_keep_hours_not_a_number(tmp_path, gen_dir) -> None:
    deps, _, _ = deps_for(tmp_path, gen_dir, FakeRunner())
    with pytest.raises(SystemExit):
        main(["keep", "soon"], deps)


def test_keep_failure_is_reported_and_redacted(tmp_path, gen_dir) -> None:
    runner = FakeRunner({"put-object": RunResult(1, "AccessDenied s3cretvalue")})
    deps, out, _ = deps_for(tmp_path, gen_dir, runner)
    assert main(["keep"], deps) == 1
    assert "AccessDenied" in out.getvalue() and "s3cretvalue" not in out.getvalue()


def test_keep_dry_run(tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, out, _ = deps_for(tmp_path, gen_dir, runner)
    assert main(["keep", "--dry-run"], deps) == 0
    assert runner.calls == [] and "Would write" in out.getvalue()


class StateRunner(FakeRunner):
    """Returns the next state from a script on each state read."""

    def __init__(self, states: list[str]) -> None:
        super().__init__()
        self.states = states

    def run(self, argv, timeout=None):
        if "s3" in argv and "cp" in argv and "state/" in " ".join(argv):
            self.calls.append(tuple(argv))
            status = self.states.pop(0) if len(self.states) > 1 else self.states[0]
            if status == "missing":
                return RunResult(1, "NoSuchKey")
            return RunResult(0, json.dumps({"status": status, "since": "2026-10-30T10:00:00Z"}))
        return super().run(argv, timeout)


def test_pause_writes_request_and_polls_until_paused(tmp_path, gen_dir) -> None:
    runner = StateRunner(["running", "running", "pausing", "paused"])
    deps, out, clock = deps_for(tmp_path, gen_dir, runner)
    assert main(["pause"], deps) == 0
    body = json.loads((tmp_path / "ws" / ".lab" / f"guard-requests-{LAB}.json").read_text(encoding="utf-8"))
    assert body == {"action": "pause", "ts": "2026-10-30T12:00:00Z"}
    call = put_calls(runner)[0]
    assert call[call.index("--key") + 1] == f"requests/{LAB}.json"
    assert clock.sleeps and "paused" in out.getvalue() and "lab down" in out.getvalue()


def test_pause_no_wait(tmp_path, gen_dir) -> None:
    runner = StateRunner(["running"])
    deps, out, clock = deps_for(tmp_path, gen_dir, runner)
    assert main(["pause", "--no-wait"], deps) == 0
    assert clock.sleeps == [] and len(put_calls(runner)) == 1
    assert "--no-wait" in out.getvalue()


def test_pause_times_out_bounded(tmp_path, gen_dir) -> None:
    runner = StateRunner(["running"])
    deps, out, clock = deps_for(tmp_path, gen_dir, runner)
    assert main(["pause"], deps) == 1
    assert 0 < len(clock.sleeps) <= 100
    assert "Still not paused" in out.getvalue()


def test_pause_when_already_paused_sends_nothing(tmp_path, gen_dir) -> None:
    runner = StateRunner(["paused"])
    deps, out, _ = deps_for(tmp_path, gen_dir, runner)
    assert main(["pause"], deps) == 0
    assert put_calls(runner) == [] and "already paused" in out.getvalue()


def test_pause_on_destroyed_lab_fails(tmp_path, gen_dir) -> None:
    runner = StateRunner(["destroyed"])
    deps, out, _ = deps_for(tmp_path, gen_dir, runner)
    assert main(["pause"], deps) == 1 and put_calls(runner) == []


def test_pause_guard_error_state(tmp_path, gen_dir) -> None:
    runner = StateRunner(["running", "error"])
    deps, out, _ = deps_for(tmp_path, gen_dir, runner)
    assert main(["pause"], deps) == 1
    assert "'error'" in out.getvalue()


def test_pause_request_write_failure(tmp_path, gen_dir) -> None:
    runner = StateRunner(["missing"])
    runner.results["put-object"] = RunResult(1, "denied")
    deps, out, _ = deps_for(tmp_path, gen_dir, runner)
    assert main(["pause"], deps) == 1 and "denied" in out.getvalue()


def test_resume_writes_request_and_heartbeat(tmp_path, gen_dir) -> None:
    runner = StateRunner(["paused", "resuming", "running"])
    deps, out, _ = deps_for(tmp_path, gen_dir, runner)
    assert main(["resume"], deps) == 0
    keys = [c[c.index("--key") + 1] for c in put_calls(runner)]
    assert keys == [f"requests/{LAB}.json", f"heartbeat/{LAB}"]
    assert "Done: your lab is running" in out.getvalue()


def wake_calls(runner: FakeRunner) -> list[tuple[str, ...]]:
    return [c for c in runner.calls if "lambda" in c and "invoke" in c]


def test_pause_wakes_the_guard_right_after_the_request(tmp_path, gen_dir) -> None:
    runner = StateRunner(["running"])
    deps, out, _ = deps_for(tmp_path, gen_dir, runner)
    assert main(["pause", "--no-wait"], deps) == 0
    assert len(wake_calls(runner)) == 1
    assert "woken" in out.getvalue() and "15 minutes" not in out.getvalue()


def test_resume_falls_back_to_the_timer_when_the_guard_cannot_be_woken(tmp_path, gen_dir) -> None:
    runner = StateRunner(["paused"])
    runner.results["lambda"] = RunResult(1, "AccessDenied")
    deps, out, _ = deps_for(tmp_path, gen_dir, runner)
    assert main(["resume", "--no-wait"], deps) == 0
    assert len(wake_calls(runner)) == 1
    assert "about every 15 minutes" in out.getvalue()


def test_resume_when_running_sends_nothing(tmp_path, gen_dir) -> None:
    runner = StateRunner(["running"])
    deps, out, _ = deps_for(tmp_path, gen_dir, runner)
    assert main(["resume"], deps) == 0 and put_calls(runner) == []


def test_resume_no_wait_still_heartbeats(tmp_path, gen_dir) -> None:
    runner = StateRunner(["paused"])
    deps, _, clock = deps_for(tmp_path, gen_dir, runner)
    assert main(["resume", "--no-wait"], deps) == 0
    assert len(put_calls(runner)) == 2 and clock.sleeps == []


SAVES = "                           PRE 20261028T010000Z/\n                           PRE 20261029T020000Z/\n                           PRE ../evil/\n"


def test_pull_list(tmp_path, gen_dir) -> None:
    runner = FakeRunner({"s3 ls": RunResult(0, SAVES)})
    deps, out, _ = deps_for(tmp_path, gen_dir, runner)
    assert main(["pull", "--list"], deps) == 0
    text = out.getvalue()
    assert text.index("20261028T010000Z") < text.index("20261029T020000Z")
    assert "evil" not in text and len(runner.calls) == 1


def test_pull_list_empty(tmp_path, gen_dir) -> None:
    deps, out, _ = deps_for(tmp_path, gen_dir, FakeRunner())
    assert main(["pull", "--list"], deps) == 0 and "No saves" in out.getvalue()


def test_pull_latest_copies_newest(tmp_path, gen_dir) -> None:
    runner = FakeRunner({"s3 ls": RunResult(0, SAVES)})
    deps, out, _ = deps_for(tmp_path, gen_dir, runner)
    assert main(["pull"], deps) == 0
    copy = runner.calls[-1]
    assert "--recursive" in copy
    assert f"s3://{BUCKET}/saves/{LAB}/20261029T020000Z/" in copy
    assert "/workspace/saves/20261029T020000Z" in copy
    assert (tmp_path / "ws" / "saves" / "20261029T020000Z").is_dir()
    assert main(["pull", "--latest"], deps) == 0


def test_pull_nothing_to_copy(tmp_path, gen_dir) -> None:
    deps, out, _ = deps_for(tmp_path, gen_dir, FakeRunner())
    assert main(["pull"], deps) == 1 and "No saves" in out.getvalue()


def test_pull_failures(tmp_path, gen_dir) -> None:
    deps, out, _ = deps_for(tmp_path, gen_dir, FakeRunner({"s3 ls": RunResult(1, "denied")}))
    assert main(["pull"], deps) == 1 and "denied" in out.getvalue()
    runner = FakeRunner({"s3 ls": RunResult(0, SAVES), "--recursive": RunResult(1, "s3cretvalue broke")})
    deps, out, _ = deps_for(tmp_path, gen_dir, runner)
    assert main(["pull"], deps) == 1
    assert "Copy failed" in out.getvalue() and "s3cretvalue" not in out.getvalue()


def test_pull_list_and_latest_conflict(tmp_path, gen_dir) -> None:
    deps, _, _ = deps_for(tmp_path, gen_dir, FakeRunner())
    with pytest.raises(SystemExit):
        main(["pull", "--list", "--latest"], deps)


def test_status_guard_not_configured(tmp_path, gen_dir) -> None:
    deps, out, _ = deps_for(tmp_path, gen_dir, FakeRunner(), guard=False)
    assert main(["status"], deps) == 0
    assert "Guard: not configured" in out.getvalue() and "GUARD_BUCKET: not set" in out.getvalue()


def test_status_guard_state_and_time_until_pause(tmp_path, gen_dir) -> None:
    runner = StateRunner(["running"])
    deps, out, clock = deps_for(tmp_path, gen_dir, runner)
    main(["keep", "1"], deps)  # records keep_until locally
    clock.now += timedelta(minutes=20)
    assert main(["status"], deps) == 0
    text = out.getvalue()
    assert "Guard state: running" in text
    assert "Pause in about 0h 40m" in text or "Pause in about 40m" in text
    assert "Last heartbeat from this computer: none" in text


def test_status_guard_unreadable_and_in_shell(tmp_path, gen_dir) -> None:
    deps, out, _ = deps_for(tmp_path, gen_dir, StateRunner(["missing"]))
    assert main(["status"], deps) == 0 and "not reported yet" in out.getvalue()
    deps2, out2, _ = deps_for(tmp_path, gen_dir, StateRunner(["paused"]), in_shell=True)
    assert main(["status"], deps2) == 0
    assert "Guard state: paused" in out2.getvalue() and "Pause in" not in out2.getvalue()


def test_pause_estimate_unknown_and_overdue() -> None:
    assert pause_estimate({}, NOW) is None
    old = {"heartbeat": "2026-10-30T08:00:00Z"}
    assert pause_estimate(old, NOW) < timedelta(0)


# ---- heartbeat in lab shell ----

def test_shell_no_heartbeat_without_guard(tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, _, _ = deps_for(tmp_path, gen_dir, runner, guard=False)
    assert main(["shell"], deps) == 0
    assert put_calls(runner) == []


def test_shell_writes_heartbeat_and_stops(tmp_path, gen_dir) -> None:
    beats = threading.Event()

    class Shell(FakeRunner):
        def run(self, argv, timeout=None):
            result = super().run(argv, timeout)
            if "put-object" in argv:
                beats.set()
            return result

        def run_interactive(self, argv):
            self.calls.append(tuple(argv))
            assert beats.wait(5), "heartbeat did not start with the shell"
            return 0

    runner = Shell()
    deps, _, _ = deps_for(tmp_path, gen_dir, runner)
    before = threading.active_count()
    assert main(["shell"], deps) == 0
    assert len(put_calls(runner)) == 1
    assert put_calls(runner)[0][put_calls(runner)[0].index("--key") + 1] == f"heartbeat/{LAB}"
    assert threading.active_count() <= before  # thread joined on exit
    assert json.loads((tmp_path / "ws" / ".lab" / "guard-local.json").read_text(encoding="utf-8"))["heartbeat"]


def test_shell_dry_run_has_no_heartbeat(tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, _, _ = deps_for(tmp_path, gen_dir, runner)
    assert main(["shell", "--dry-run"], deps) == 0 and put_calls(runner) == []


def test_shell_heartbeat_failure_does_not_block_shell(tmp_path, gen_dir) -> None:
    class Shell(FakeRunner):
        def run_interactive(self, argv):
            self.calls.append(tuple(argv))
            return 7

    runner = Shell({"put-object": RunResult(1, "denied s3cretvalue")})
    deps, out, _ = deps_for(tmp_path, gen_dir, runner)
    assert main(["shell"], deps) == 7
    assert "denied" in out.getvalue() and "s3cretvalue" not in out.getvalue()


def test_heartbeat_loop_beats_each_interval_and_reports_once() -> None:
    waits: list[float] = []
    answers = iter([False, False, False, True])
    reports: list[str] = []
    beats: list[int] = []

    def beat() -> str:
        beats.append(1)
        return "boom"

    def wait(seconds: float) -> bool:
        waits.append(seconds)
        return next(answers)

    Heartbeat(beat, reports.append, interval=600, wait=wait).run()
    assert len(beats) == 4 and waits == [600] * 4
    assert len(reports) == 1 and "boom" in reports[0] and "lab down" in reports[0]


def test_heartbeat_survives_exceptions_and_recovers() -> None:
    outcomes = iter([OSError("no engine"), ""])
    reports: list[str] = []

    def beat() -> str:
        result = next(outcomes)
        if isinstance(result, Exception):
            raise result
        return result

    stops = iter([False, True])
    Heartbeat(beat, reports.append, wait=lambda s: next(stops)).run()
    assert len(reports) == 1 and "no engine" in reports[0]


def test_heartbeat_thread_stop_is_prompt() -> None:
    started = threading.Event()
    hb = Heartbeat(lambda: (started.set(), "")[1], lambda m: None, interval=3600)
    hb.start()
    assert started.wait(5)
    hb.stop()
    assert not hb._thread.is_alive()

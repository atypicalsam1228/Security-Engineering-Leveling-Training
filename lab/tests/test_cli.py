from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from conftest import FakeRunner
from labcli.cli import Deps, main
from labcli.executor import RunResult


def make_deps(tmp_path: Path, gen_dir: Path, runner, answers=("destroy",), in_shell=False, extra_environ=None):
    out = io.StringIO()
    states = tmp_path / "states"
    (states / "eng-0").mkdir(parents=True, exist_ok=True)
    (states / "eng-0" / "10-ns.yaml").write_text("kind: Namespace", encoding="utf-8")
    (tmp_path / "tf").mkdir(exist_ok=True)
    (tmp_path / "tf" / "main.tf").write_text("", encoding="utf-8")
    it = iter(answers)
    environ = {
        "LAB_WORKSPACE": str(tmp_path / "ws"),
        "LAB_GENERATORS_DIR": str(gen_dir),
        "LAB_STATES_DIR": str(states),
        "LAB_TERRAFORM_DIR": str(tmp_path / "tf"),
        "LOKI_PASSWORD": "s3cretvalue",
    }
    if in_shell:
        environ["LAB_IN_SHELL"] = "1"
    environ.update(extra_environ or {})
    deps = Deps(runner=runner, out=out, ask=lambda prompt: next(it), which=lambda n: f"/bin/{n}", environ=environ)
    return deps, out


def test_modules_lists(tmp_path, gen_dir) -> None:
    deps, out = make_deps(tmp_path, gen_dir, FakeRunner())
    assert main(["modules"], deps) == 0
    text = out.getvalue()
    assert text.index("ENG-0") < text.index("GRC-2")


def test_shell_dry_run_does_not_run(tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, out = make_deps(tmp_path, gen_dir, runner)
    assert main(["shell", "--dry-run"], deps) == 0
    assert runner.calls == []
    assert "would run" in out.getvalue() and "podman" in out.getvalue()
    assert "s3cretvalue" not in out.getvalue()


def test_shell_runs(tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, _ = make_deps(tmp_path, gen_dir, runner)
    assert main(["shell"], deps) == 0
    assert runner.calls[0][0] == "podman"


def test_shell_inside_shell_refused(tmp_path, gen_dir) -> None:
    deps, out = make_deps(tmp_path, gen_dir, FakeRunner(), in_shell=True)
    assert main(["shell"], deps) == 2
    assert "already" in out.getvalue()


def test_no_engine_error(tmp_path, gen_dir) -> None:
    deps, out = make_deps(tmp_path, gen_dir, FakeRunner())
    deps = Deps(deps.runner, deps.out, deps.ask, lambda n: None, deps.environ)
    assert main(["shell"], deps) == 2
    assert "podman" in out.getvalue()


def test_start_dry_run(tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, out = make_deps(tmp_path, gen_dir, runner)
    assert main(["start", "eng-0", "--dry-run"], deps) == 0
    assert runner.calls == []
    assert "10-ns.yaml" in out.getvalue()
    assert not (tmp_path / "ws" / ".lab" / "modules.json").exists()


def test_start_applies_and_records(tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, _ = make_deps(tmp_path, gen_dir, runner)
    assert main(["start", "ENG-0"], deps) == 0
    assert "apply" in runner.calls[0]
    data = json.loads((tmp_path / "ws" / ".lab" / "modules.json").read_text(encoding="utf-8"))
    assert data["ENG-0"]["action"] == "start"


def test_start_step_failure(tmp_path, gen_dir) -> None:
    runner = FakeRunner({"apply": RunResult(1, "boom")})
    deps, out = make_deps(tmp_path, gen_dir, runner)
    assert main(["start", "eng-0"], deps) == 1
    assert "boom" in out.getvalue()


def test_start_unknown_module(tmp_path, gen_dir) -> None:
    deps, _ = make_deps(tmp_path, gen_dir, FakeRunner())
    assert main(["start", "zzz"], deps) == 2


def test_start_without_state_dir(tmp_path, gen_dir) -> None:
    deps, out = make_deps(tmp_path, gen_dir, FakeRunner())
    assert main(["reset", "grc-2"], deps) == 1
    assert "No start state" in out.getvalue()


def test_start_todo_is_reported(tmp_path, gen_dir) -> None:
    deps, out = make_deps(tmp_path, gen_dir, FakeRunner())
    (tmp_path / "states" / "eng-0" / "TODO.md").write_text("- [live] 1: need things", encoding="utf-8")
    assert main(["start", "eng-0"], deps) == 0
    assert "INCOMPLETE" in out.getvalue()


def test_up_dry_run(tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, out = make_deps(tmp_path, gen_dir, runner)
    assert main(["up", "--dry-run"], deps) == 0
    assert runner.calls == [] and "cost" in out.getvalue().lower() and "apply" in out.getvalue()


def test_up_declined(tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, _ = make_deps(tmp_path, gen_dir, runner, answers=("no",))
    assert main(["up"], deps) == 1
    assert runner.calls == []


def test_up_runs_and_writes_env(tmp_path, gen_dir) -> None:
    out_json = json.dumps({"kms_key_arn": {"value": "arn:k"}})
    runner = FakeRunner({" output ": RunResult(0, out_json)})
    deps, _ = make_deps(tmp_path, gen_dir, runner, answers=("yes",))
    assert main(["up", "--skip-cluster"], deps) == 0
    env_file = tmp_path / "ws" / ".lab" / "lab.env"
    text = env_file.read_text(encoding="utf-8")
    assert "KMS_KEY_ARN=arn:k\n" in text
    assert "LOKI_PASSWORD=" in text and "GRAFANA_PASSWORD=" in text and "KEYCLOAK_ADMIN_PASSWORD=" in text


def test_up_apply_failure(tmp_path, gen_dir) -> None:
    runner = FakeRunner({" apply ": RunResult(1, "quota")})
    deps, out = make_deps(tmp_path, gen_dir, runner)
    assert main(["up", "--yes"], deps) == 1
    assert "lab down" in out.getvalue()


def test_up_without_terraform_files(tmp_path, gen_dir) -> None:
    deps, out = make_deps(tmp_path, gen_dir, FakeRunner())
    (tmp_path / "tf" / "main.tf").unlink()
    assert main(["up", "--yes"], deps) == 1
    assert "TODO" in out.getvalue()


def test_down_requires_confirmation(tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, out = make_deps(tmp_path, gen_dir, runner, answers=("nope",))
    assert main(["down"], deps) == 1
    assert runner.calls == []
    assert "WARNING" in out.getvalue()


def test_down_confirmed(tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, out = make_deps(tmp_path, gen_dir, runner, answers=("destroy",))
    assert main(["down"], deps) == 0
    assert any("destroy" in c for c in runner.calls[-1])
    assert "verify" in out.getvalue().lower()


def test_down_failure_is_loud(tmp_path, gen_dir) -> None:
    runner = FakeRunner({"destroy": RunResult(1, "denied")})
    deps, out = make_deps(tmp_path, gen_dir, runner)
    assert main(["down", "--yes"], deps) == 1
    assert "STILL" in out.getvalue()


def test_down_dry_run_and_yes(tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, out = make_deps(tmp_path, gen_dir, runner)
    assert main(["down", "--dry-run"], deps) == 0
    assert runner.calls == []
    assert main(["down", "--yes"], deps) == 0
    assert runner.calls


def test_status(tmp_path, gen_dir) -> None:
    deps, out = make_deps(tmp_path, gen_dir, FakeRunner())
    assert main(["status"], deps) == 0
    text = out.getvalue()
    assert "podman" in text and "LOKI_PASSWORD: set" in text and "s3cretvalue" not in text


def test_no_args_prints_help(tmp_path, gen_dir) -> None:
    deps, out = make_deps(tmp_path, gen_dir, FakeRunner())
    assert main([], deps) == 2


def test_runner_error_handled(tmp_path, gen_dir) -> None:
    class Boom(FakeRunner):
        def run(self, argv, timeout=None):
            raise OSError("no such file")

    deps, out = make_deps(tmp_path, gen_dir, Boom())
    assert main(["start", "eng-0"], deps) == 1
    assert "no such file" in out.getvalue()


def test_missing_generators(tmp_path, gen_dir) -> None:
    deps, _ = make_deps(tmp_path, gen_dir, FakeRunner())
    bad = Deps(deps.runner, deps.out, deps.ask, deps.which, {**deps.environ, "LAB_GENERATORS_DIR": str(tmp_path / "x")})
    assert main(["modules"], bad) == 2


@pytest.mark.parametrize("cmd", ["start", "reset"])
def test_module_commands_require_arg(cmd, tmp_path, gen_dir) -> None:
    deps, _ = make_deps(tmp_path, gen_dir, FakeRunner())
    with pytest.raises(SystemExit):
        main([cmd], deps)


def test_todo_only_state_fails(tmp_path, gen_dir) -> None:
    deps, out = make_deps(tmp_path, gen_dir, FakeRunner())
    d = tmp_path / "states" / "grc-2"
    d.mkdir()
    (d / "TODO.md").write_text("- needs a thing", encoding="utf-8")
    assert main(["start", "grc-2"], deps) == 1
    assert "INCOMPLETE" in out.getvalue() and "needs a thing" in out.getvalue()


def test_shell_creates_workspace(tmp_path, gen_dir) -> None:
    deps, _ = make_deps(tmp_path, gen_dir, FakeRunner())
    main(["shell"], deps)
    assert (tmp_path / "ws").is_dir()


def test_up_in_shell_refused(tmp_path, gen_dir) -> None:
    deps, out = make_deps(tmp_path, gen_dir, FakeRunner(), in_shell=True)
    assert main(["up"], deps) == 2 and main(["down"], deps) == 2


def test_status_inside_shell_and_records(tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, out = make_deps(tmp_path, gen_dir, runner)
    main(["start", "eng-0"], deps)
    main(["status"], deps)
    assert "ENG-0 (start)" in out.getvalue()
    deps2, out2 = make_deps(tmp_path, gen_dir, runner, in_shell=True)
    main(["status"], deps2)
    assert "inside lab shell" in out2.getvalue()

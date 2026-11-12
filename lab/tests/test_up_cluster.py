"""lab up / lab down with the cluster install step. No AWS, no containers."""
from __future__ import annotations

from pathlib import Path

from conftest import FakeRunner
from labcli.cli import main
from labcli.environment import LabEnv, workspace_container_path
from labcli.executor import RunResult
from labcli.terraform import cluster_destroy_argv, install_argv
from test_cli import make_deps


def _secret(tmp_path: Path) -> Path:
    path = tmp_path / "ws" / "pull-secret.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"auths": {}}', encoding="utf-8")
    return path


def _joined(calls) -> list[str]:
    return [" ".join(c) for c in calls]


def test_install_argv_shapes() -> None:
    assert install_argv() == ("bash", "/lab/terraform/scripts/lab-install.sh")
    assert cluster_destroy_argv() == ("bash", "/lab/terraform/scripts/lab-install.sh", "destroy")


def test_path_translation_posix_and_outside(tmp_path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    assert workspace_container_path(ws, str(ws / "a" / "s.json")) == "/workspace/a/s.json"
    assert workspace_container_path(ws, str(tmp_path / "elsewhere.json")) is None
    assert workspace_container_path(ws, str(ws / ".." / "x.json")) is None
    assert workspace_container_path(ws, str(ws)) is None


def test_path_translation_windows_paths() -> None:
    ws = "C:\\Users\\sam\\lab-workspace"
    assert workspace_container_path(ws, "C:\\Users\\sam\\lab-workspace\\keys\\ps.json") == "/workspace/keys/ps.json"
    assert workspace_container_path(ws, "c:/users/sam/lab-workspace/ps.json") == "/workspace/ps.json"
    assert workspace_container_path(ws, "C:\\Users\\sam\\Downloads\\ps.json") is None
    assert workspace_container_path(ws, "C:\\Users\\sam\\lab-workspace\\..\\x.json") is None


def test_wrap_overrides_do_not_duplicate_passthrough(tmp_path) -> None:
    env = LabEnv("docker", "img", tmp_path, tmp_path, tmp_path, False)
    argv = env.wrap(("true",), extra_pass=("BASE_DOMAIN",), extra_env={"PULL_SECRET_FILE": "/workspace/p.json"})
    assert "PULL_SECRET_FILE=/workspace/p.json" in argv
    assert argv.count("BASE_DOMAIN") == 1
    assert "PULL_SECRET_FILE" not in argv


def test_up_dry_run_shows_install_and_translated_path(tmp_path, gen_dir) -> None:
    secret = _secret(tmp_path)
    runner = FakeRunner()
    deps, out = make_deps(tmp_path, gen_dir, runner, extra_environ={"PULL_SECRET_FILE": str(secret)})
    assert main(["up", "--dry-run"], deps) == 0
    text = out.getvalue()
    assert runner.calls == []
    assert "lab-install.sh" in text and "PULL_SECRET_FILE=/workspace/pull-secret.json" in text
    assert "BASE_DOMAIN" in text
    assert str(secret) not in text and "auths" not in text


def test_up_dry_run_without_pull_secret_notes_it(tmp_path, gen_dir) -> None:
    deps, out = make_deps(tmp_path, gen_dir, FakeRunner())
    assert main(["up", "--dry-run"], deps) == 0
    assert "PULL_SECRET_FILE is not set" in out.getvalue()


def test_up_dry_run_skip_cluster(tmp_path, gen_dir) -> None:
    deps, out = make_deps(tmp_path, gen_dir, FakeRunner())
    assert main(["up", "--dry-run", "--skip-cluster"], deps) == 0
    assert "lab-install.sh" not in out.getvalue() and "skip-cluster" in out.getvalue()


def test_up_requires_pull_secret_before_building(tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, out = make_deps(tmp_path, gen_dir, runner)
    assert main(["up", "--yes"], deps) == 1
    assert runner.calls == []
    assert "PULL_SECRET_FILE" in out.getvalue() and "Nothing was built" in out.getvalue()


def test_up_rejects_pull_secret_outside_workspace(tmp_path, gen_dir) -> None:
    outside = tmp_path / "Downloads" / "ps.json"
    outside.parent.mkdir()
    outside.write_text("{}", encoding="utf-8")
    runner = FakeRunner()
    deps, out = make_deps(tmp_path, gen_dir, runner, extra_environ={"PULL_SECRET_FILE": str(outside)})
    assert main(["up", "--yes"], deps) == 1
    assert runner.calls == [] and "under the lab workspace" in out.getvalue()


def test_up_runs_install_after_apply(tmp_path, gen_dir) -> None:
    secret = _secret(tmp_path)
    runner = FakeRunner()
    deps, out = make_deps(tmp_path, gen_dir, runner, extra_environ={"PULL_SECRET_FILE": str(secret)})
    assert main(["up", "--yes"], deps) == 0
    calls = _joined(runner.calls)
    apply_i = next(i for i, c in enumerate(calls) if " apply " in c)
    install_i = next(i for i, c in enumerate(calls) if "lab-install.sh" in c)
    assert apply_i < install_i
    assert "PULL_SECRET_FILE=/workspace/pull-secret.json" in calls[install_i]
    assert "/lab/terraform" in calls[install_i]
    assert str(secret) not in calls[install_i]


def test_up_skip_cluster_runs_no_install(tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, out = make_deps(tmp_path, gen_dir, runner)
    assert main(["up", "--yes", "--skip-cluster"], deps) == 0
    assert not any("lab-install.sh" in c for c in _joined(runner.calls))
    assert "no cluster was installed" in out.getvalue()


def test_up_install_failure_is_loud(tmp_path, gen_dir) -> None:
    secret = _secret(tmp_path)
    runner = FakeRunner({"lab-install.sh": RunResult(3, "timeout")})
    deps, out = make_deps(tmp_path, gen_dir, runner, extra_environ={"PULL_SECRET_FILE": str(secret)})
    assert main(["up", "--yes"], deps) == 1
    assert "lab down" in out.getvalue()


def test_down_destroys_cluster_before_terraform(tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, _ = make_deps(tmp_path, gen_dir, runner)
    assert main(["down", "--yes"], deps) == 0
    calls = _joined(runner.calls)
    assert "lab-init.sh" in calls[0]  # points Terraform at this lab's state first
    assert "lab-install.sh destroy" in calls[1]
    assert "terraform" in calls[2] and " destroy " in calls[2]


def test_down_stops_if_cluster_not_destroyed(tmp_path, gen_dir) -> None:
    runner = FakeRunner({"lab-install.sh destroy": RunResult(3, "timeout")})
    deps, out = make_deps(tmp_path, gen_dir, runner)
    assert main(["down", "--yes"], deps) == 1
    assert len(runner.calls) == 2
    assert "STILL RUNNING" in out.getvalue()


def test_down_dry_run_lists_both_steps(tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, out = make_deps(tmp_path, gen_dir, runner)
    assert main(["down", "--dry-run"], deps) == 0
    text = out.getvalue()
    assert runner.calls == [] and text.index("lab-install.sh") < text.index("-chdir")

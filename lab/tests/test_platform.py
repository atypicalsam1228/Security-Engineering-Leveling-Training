"""lab platform: installs the in-lab services after the cluster. No AWS, no containers."""
from __future__ import annotations

from conftest import FakeRunner
from labcli.cli import main
from labcli.environment import LabEnv
from labcli.terraform import platform_argv
from test_cli import make_deps


def test_platform_argv_shapes() -> None:
    assert platform_argv() == ("bash", "/lab/platform/install.sh")
    assert platform_argv("20") == ("bash", "/lab/platform/install.sh", "--only", "20")


def test_wrap_mounts_platform_read_only(tmp_path) -> None:
    env = LabEnv("docker", "img", tmp_path, tmp_path, tmp_path, False, platform_dir=tmp_path / "plat")
    argv = env.wrap(("true",), platform=True)
    assert any(a.endswith(":/lab/platform:ro") for a in argv)


def test_platform_dry_run_prints_the_install_command(tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, out = make_deps(tmp_path, gen_dir, runner)
    assert main(["platform", "--dry-run", "--only", "20"], deps) == 0
    assert runner.calls == []
    assert "/lab/platform/install.sh --only 20" in out.getvalue()


def test_platform_without_a_cluster_stops_with_a_message(tmp_path, gen_dir) -> None:
    runner = FakeRunner()
    deps, out = make_deps(tmp_path, gen_dir, runner)
    assert main(["platform"], deps) == 1
    assert "lab up" in out.getvalue()
    assert runner.calls == []


def test_up_dry_run_lists_the_platform_step(tmp_path, gen_dir) -> None:
    deps, out = make_deps(tmp_path, gen_dir, FakeRunner())
    assert main(["up", "--dry-run"], deps) == 0
    assert "/lab/platform/install.sh" in out.getvalue()

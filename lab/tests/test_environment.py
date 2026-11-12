from __future__ import annotations

from pathlib import Path

import pytest

from labcli.environment import EngineNotFoundError, LabEnv, detect_engine


def make_env(tmp_path: Path, in_shell: bool = False) -> LabEnv:
    return LabEnv(
        engine="podman",
        image="img:1",
        workspace=tmp_path / "ws",
        states_dir=tmp_path / "states",
        terraform_dir=tmp_path / "tf",
        in_shell=in_shell,
        passthrough=("LOKI_URL", "LOKI_PASSWORD"),
    )


def test_detect_prefers_podman() -> None:
    assert detect_engine(lambda n: f"/bin/{n}") == "podman"


def test_detect_docker_fallback() -> None:
    assert detect_engine(lambda n: "/bin/docker" if n == "docker" else None) == "docker"


def test_detect_override() -> None:
    assert detect_engine(lambda n: None, override="docker") == "docker"


def test_detect_none() -> None:
    with pytest.raises(EngineNotFoundError):
        detect_engine(lambda n: None)


def test_shell_argv_passes_names_not_values(tmp_path: Path) -> None:
    argv = make_env(tmp_path).shell_argv()
    assert argv[:3] == ("podman", "run", "--rm")
    assert "-it" in argv
    assert "LOKI_PASSWORD" in argv
    assert not any("=" in a and "PASSWORD" in a for a in argv)
    assert "img:1" in argv and argv[-1] == "bash"
    assert any(a.endswith(":/workspace") for a in argv)


def test_env_file_only_if_present(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    assert "--env-file" not in env.shell_argv()
    env.env_file.parent.mkdir(parents=True, exist_ok=True)
    env.env_file.write_text("A=b\n", encoding="utf-8")
    assert "--env-file" in env.shell_argv()


def test_wrap_in_container_vs_in_shell(tmp_path: Path) -> None:
    outer = make_env(tmp_path).wrap(("oc", "get", "pods"))
    assert outer[0] == "podman" and outer[-3:] == ("oc", "get", "pods")
    assert "-it" not in outer
    assert make_env(tmp_path, in_shell=True).wrap(("oc", "get", "pods")) == ("oc", "get", "pods")


def test_wrap_mounts_states_readonly(tmp_path: Path) -> None:
    argv = make_env(tmp_path).wrap(("true",), states=True)
    assert any(a.endswith(":/lab/states:ro") for a in argv)


def test_wrap_mounts_terraform(tmp_path: Path) -> None:
    argv = make_env(tmp_path).wrap(("true",), terraform=True)
    assert any(a.endswith(":/lab/terraform") for a in argv)


def test_shell_argv_inside_shell_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        make_env(tmp_path, in_shell=True).shell_argv()


def test_home_is_inside_the_workspace_and_created(tmp_path: Path) -> None:
    argv = make_env(tmp_path).shell_argv()
    assert "HOME=/workspace/.lab/home" in argv
    assert (tmp_path / "ws" / ".lab" / "home").is_dir()


def test_ca_bundle_is_trusted_only_when_the_platform_wrote_it(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    assert not any(a.startswith("SSL_CERT_FILE=") for a in env.shell_argv())
    (env.state_dir / "ca-bundle.crt").write_text("x", encoding="utf-8")
    argv = env.shell_argv()
    for name in ("SSL_CERT_FILE", "CURL_CA_BUNDLE", "GIT_SSL_CAINFO", "REQUESTS_CA_BUNDLE"):
        assert f"{name}=/workspace/.lab/ca-bundle.crt" in argv


def test_rootless_podman_runs_as_the_login_user(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("os.getuid", lambda: 1002, raising=False)
    monkeypatch.setattr("os.getgid", lambda: 1002, raising=False)
    argv = make_env(tmp_path).shell_argv()
    assert argv[:9] == ("podman", "run", "--rm", "--userns=keep-id", "--user", "1002:1002", "--security-opt", "label=disable", "-it")


def test_docker_gets_no_user_mapping(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("os.getuid", lambda: 1002, raising=False)
    env = make_env(tmp_path)
    docker_env = LabEnv(engine="docker", image=env.image, workspace=env.workspace, states_dir=env.states_dir,
                        terraform_dir=env.terraform_dir, in_shell=False)
    assert "--userns=keep-id" not in docker_env.shell_argv()


def test_no_user_mapping_where_the_platform_has_no_user_ids(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr("os.getuid", raising=False)
    assert "--userns=keep-id" not in make_env(tmp_path).shell_argv()

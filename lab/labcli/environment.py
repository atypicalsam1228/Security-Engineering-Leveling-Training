"""Tools-container environment: engine detection and command wrapping."""
from __future__ import annotations

import ntpath
import os
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

ENGINES = ("podman", "docker")
DEFAULT_IMAGE = "lab-tools:latest"
CONTAINER_WORKSPACE = "/workspace"
CONTAINER_STATES = "/lab/states"
CONTAINER_TERRAFORM = "/lab/terraform"
CONTAINER_PLATFORM = "/lab/platform"
KUBECONFIG_IN_CONTAINER = "/workspace/.lab/kubeconfig"
# The container is deleted on exit, so HOME lives in the workspace to keep the learner's files.
HOME_IN_CONTAINER = "/workspace/.lab/home"
# Written by the platform install: system CAs plus the cluster ingress CA, so curl, git and python trust the in-lab services.
CA_BUNDLE_IN_CONTAINER = "/workspace/.lab/ca-bundle.crt"
CA_BUNDLE_VARS = ("SSL_CERT_FILE", "CURL_CA_BUNDLE", "GIT_SSL_CAINFO", "REQUESTS_CA_BUNDLE")

CONTRACT_VARS = (
    "LAB_ID AWS_REGION CLUSTER_NAME CLUSTER_API LOKI_URL LOKI_CA_FILE LOKI_USER LOKI_PASSWORD "
    "GRAFANA_URL GRAFANA_USER GRAFANA_PASSWORD MM_URL MM_WEBHOOK_URL KEYCLOAK_URL GITEA_INTERNAL_URL "
    "KEYCLOAK_ADMIN_USER KEYCLOAK_ADMIN_PASSWORD GITEA_URL GITEA_USER GITEA_TOKEN ARGOCD_URL "
    "REGISTRY_HOST LOG_BUCKET ARTIFACTS_BUCKET BASTION_ID KMS_KEY_ARN VPC_ID GUARD_BUCKET"
).split()

AWS_VARS = (
    "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
    "AWS_PROFILE", "AWS_DEFAULT_REGION",
)

# Variables read by lab-install.sh. BASE_DOMAIN is passed by name; the two file
# variables are paths, translated to container paths and passed as name=value.
INSTALL_PASSTHROUGH = ("BASE_DOMAIN",)
INSTALL_FILE_VARS = ("PULL_SECRET_FILE", "SSH_PUBLIC_KEY_FILE")

_WINDOWS_PATH = re.compile(r"^[A-Za-z]:[\\/]")

SECRET_MARKERS = ("PASSWORD", "TOKEN", "SECRET", "ACCESS_KEY")


class EngineNotFoundError(RuntimeError):
    """Neither podman nor docker is installed."""


def _rootless_user_args(engine: str) -> list[str]:
    """Rootless podman remaps user ids, so files owned by the login user look foreign inside the
    container and are unreadable. keep-id runs the container as the same user as the login. On RHEL,
    SELinux also blocks the container from reading the mounted folders, so its labels are turned off."""
    if engine != "podman" or not hasattr(os, "getuid"):
        return []
    return ["--userns=keep-id", "--user", f"{os.getuid()}:{os.getgid()}", "--security-opt", "label=disable"]


def detect_engine(which: Callable[[str], str | None], override: str | None = None) -> str:
    if override:
        return override
    for name in ENGINES:
        if which(name):
            return name
    raise EngineNotFoundError("Install podman or docker, then try again.")


def workspace_container_path(workspace: Path | str, host_path: str) -> str | None:
    """Translate a host path under the workspace to its path inside the container.

    Returns None when the path is not under the workspace. Windows drive paths are
    handled as Windows paths on any platform and always come back with forward slashes.
    """
    raw, base = str(host_path).strip(), str(workspace)
    if _WINDOWS_PATH.match(raw) and _WINDOWS_PATH.match(base):
        full, root = PureWindowsPath(ntpath.normpath(raw)), PureWindowsPath(ntpath.normpath(base))
    else:
        full = PurePosixPath(Path(raw).expanduser().resolve().as_posix())
        root = PurePosixPath(Path(base).expanduser().resolve().as_posix())
    pieces = full.relative_to(root).parts if full.is_relative_to(root) else None
    if not pieces:
        return None
    return CONTAINER_WORKSPACE + "/" + "/".join(pieces)


def is_secret_name(name: str) -> bool:
    return any(marker in name for marker in SECRET_MARKERS)


@dataclass(frozen=True)
class LabEnv:
    engine: str
    image: str
    workspace: Path
    states_dir: Path
    terraform_dir: Path
    in_shell: bool
    platform_dir: Path = Path("platform")
    passthrough: tuple[str, ...] = tuple(CONTRACT_VARS) + AWS_VARS

    @property
    def state_dir(self) -> Path:
        return self.workspace / ".lab"

    @property
    def env_file(self) -> Path:
        return self.state_dir / "lab.env"

    def _base(
        self,
        interactive: bool,
        mounts: tuple[str, ...],
        extra_pass: tuple[str, ...] = (),
        extra_env: Mapping[str, str] | None = None,
    ) -> list[str]:
        overrides = dict(extra_env or {})
        (self.state_dir / "home").mkdir(parents=True, exist_ok=True)
        argv = [self.engine, "run", "--rm"]
        argv += _rootless_user_args(self.engine)
        argv += ["-it"] if interactive else ["-i"]
        argv += ["-v", f"{self.workspace.as_posix()}:{CONTAINER_WORKSPACE}", "-w", CONTAINER_WORKSPACE]
        for mount in mounts:
            argv += ["-v", mount]
        argv += ["-e", "LAB_IN_SHELL=1", "-e", f"KUBECONFIG={KUBECONFIG_IN_CONTAINER}", "-e", f"HOME={HOME_IN_CONTAINER}"]
        if (self.state_dir / "ca-bundle.crt").is_file():
            for name in CA_BUNDLE_VARS:
                argv += ["-e", f"{name}={CA_BUNDLE_IN_CONTAINER}"]
        if self.env_file.is_file():
            argv += ["--env-file", str(self.env_file)]
        for name in self.passthrough + extra_pass:
            if name not in overrides:
                argv += ["-e", name]  # name only: the value is inherited, never put on the command line
        for name, value in overrides.items():
            argv += ["-e", f"{name}={value}"]  # only for non-secret values such as container paths
        return argv

    def shell_argv(self) -> tuple[str, ...]:
        if self.in_shell:
            raise ValueError("Already inside the lab shell.")
        mounts = (f"{self.states_dir.as_posix()}:{CONTAINER_STATES}:ro",)
        return tuple(self._base(True, mounts)) + (self.image, "bash")

    def wrap(
        self,
        argv: tuple[str, ...],
        states: bool = False,
        terraform: bool = False,
        platform: bool = False,
        extra_pass: tuple[str, ...] = (),
        extra_env: Mapping[str, str] | None = None,
    ) -> tuple[str, ...]:
        """Return argv that runs inside the tools container (unchanged if already inside).

        extra_pass: more variable names inherited by name. extra_env: name=value pairs
        (container paths only, never secrets).
        """
        if self.in_shell:
            return argv
        mounts: list[str] = []
        if states:
            mounts.append(f"{self.states_dir.as_posix()}:{CONTAINER_STATES}:ro")
        if terraform:
            mounts.append(f"{self.terraform_dir.as_posix()}:{CONTAINER_TERRAFORM}")
        if platform:
            mounts.append(f"{self.platform_dir.as_posix()}:{CONTAINER_PLATFORM}:ro")
        return tuple(self._base(False, tuple(mounts), extra_pass, extra_env)) + (self.image,) + argv

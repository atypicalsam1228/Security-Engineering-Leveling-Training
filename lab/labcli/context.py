"""Runtime dependencies and configuration shared by every command."""
from __future__ import annotations

import shlex
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

from labcli.catalog import Catalog, load_catalog
from labcli.environment import (
    CONTRACT_VARS,
    DEFAULT_IMAGE,
    EngineNotFoundError,
    LabEnv,
    detect_engine,
    is_secret_name,
)
from labcli.executor import Runner

LAB_ROOT = Path(__file__).resolve().parents[1]

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2


@dataclass(frozen=True)
class Deps:
    runner: Runner
    out: TextIO
    ask: Callable[[str], str]
    which: Callable[[str], str | None]
    environ: Mapping[str, str]
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    sleep: Callable[[float], None] = time.sleep


def _terraform_var_name(name: str) -> str:
    """TF_VAR_<variable> with a lowercase variable name.

    Python upper-cases environment names on Windows, but Terraform variable names are
    lowercase and case-sensitive inside the Linux container. Docker finds the value by
    name case-insensitively on Windows, so passing the lowercase name keeps both right.
    """
    return "TF_VAR_" + name[len("TF_VAR_"):].lower()


@dataclass(frozen=True)
class Ctx:
    deps: Deps

    def say(self, text: str = "") -> None:
        self.deps.out.write(text + "\n")

    @property
    def in_shell(self) -> bool:
        return self.deps.environ.get("LAB_IN_SHELL") == "1"

    def _path(self, key: str, default: Path) -> Path:
        value = self.deps.environ.get(key)
        return Path(value) if value else default

    @property
    def generators_dir(self) -> Path:
        return self._path("LAB_GENERATORS_DIR", LAB_ROOT.parent / "generators")

    @property
    def workspace(self) -> Path:
        return self._path("LAB_WORKSPACE", Path.home() / "lab-workspace")

    def lab_states_dir(self) -> Path:
        return self._path("LAB_STATES_DIR", LAB_ROOT / "states")

    def catalog(self) -> Catalog:
        return load_catalog(self.generators_dir)

    def lab_env(self) -> LabEnv:
        """Build the container environment. Raises EngineNotFoundError if none is installed."""
        engine = "" if self.in_shell else detect_engine(self.deps.which, self.deps.environ.get("LAB_ENGINE"))
        return LabEnv(
            engine=engine,
            image=self.deps.environ.get("LAB_IMAGE", DEFAULT_IMAGE),
            workspace=self.workspace,
            states_dir=self.lab_states_dir(),
            terraform_dir=self._path("LAB_TERRAFORM_DIR", LAB_ROOT.parent / "terraform"),
            in_shell=self.in_shell,
            platform_dir=self._path("LAB_PLATFORM_DIR", LAB_ROOT / "platform"),
            passthrough=LabEnv.passthrough + tuple(sorted(_terraform_var_name(n) for n in self.deps.environ if n.upper().startswith("TF_VAR_"))),
        )

    def secrets(self) -> tuple[str, ...]:
        """Values of secret-looking lab variables, used only to redact output."""
        names = [n for n in CONTRACT_VARS if is_secret_name(n)]
        return tuple(self.deps.environ[n] for n in names if self.deps.environ.get(n))

    def show(self, argv: tuple[str, ...]) -> None:
        self.say("  would run: " + shlex.join(argv))


def engine_or_none(ctx: Ctx) -> LabEnv | None:
    """Return the lab env, or print install guidance and return None."""
    try:
        return ctx.lab_env()
    except EngineNotFoundError as err:
        ctx.say(f"ERROR: {err} Lab shell needs podman or docker.")
        return None

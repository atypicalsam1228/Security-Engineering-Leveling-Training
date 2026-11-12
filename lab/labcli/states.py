"""Plan the ordered steps that apply a module's starting state."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from labcli.environment import CONTAINER_STATES

MANIFEST_SUFFIXES = (".yaml", ".yml", ".json")
SCRIPT_SUFFIX = ".sh"
RESET_DIR = "reset.d"
TODO_FILE = "TODO.md"


@dataclass(frozen=True)
class Step:
    name: str
    argv: tuple[str, ...]


@dataclass(frozen=True)
class StatePlan:
    steps: tuple[Step, ...]
    todo: str
    missing: bool


def _step_for(path: Path, state_name: str, label: str) -> Step | None:
    container_path = f"{CONTAINER_STATES}/{state_name}/{label}"
    if path.suffix == SCRIPT_SUFFIX:
        return Step(label, ("bash", container_path))
    if path.suffix in MANIFEST_SUFFIXES:
        return Step(label, ("oc", "apply", "-f", container_path))
    return None


def _steps_in(directory: Path, state_name: str, prefix: str) -> list[Step]:
    if not directory.is_dir():
        return []
    steps = (_step_for(p, state_name, prefix + p.name) for p in sorted(directory.iterdir()) if p.is_file())
    return [s for s in steps if s is not None]


def plan_state(state_dir: Path, state_name: str, reset: bool) -> StatePlan:
    """Ordered steps. Scripts must be idempotent; manifests use 'oc apply'."""
    if not state_dir.is_dir():
        return StatePlan((), "", True)
    steps: list[Step] = []
    if reset:
        steps += _steps_in(state_dir / RESET_DIR, state_name, RESET_DIR + "/")
    steps += _steps_in(state_dir, state_name, "")
    todo_path = state_dir / TODO_FILE
    todo = todo_path.read_text(encoding="utf-8") if todo_path.is_file() else ""
    return StatePlan(tuple(steps), todo, False)

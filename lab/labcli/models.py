"""Immutable data types shared across the lab CLI."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Fault:
    """One named, reversible break a learner can apply to practice spotting it."""

    id: str
    title: str
    break_code: str
    restore_code: str


@dataclass(frozen=True)
class ModuleSpec:
    """Per-module metadata derived from generators/content."""

    id: str
    title: str
    position: int
    total: int
    prereq: tuple[str, ...]
    env: tuple[str, ...]
    needs: tuple[str, ...]
    minutes: int
    faults: tuple[Fault, ...] = ()
    optional: bool = False

    @property
    def state_name(self) -> str:
        """Directory name under states/ (lower-case module id)."""
        return self.id.lower()

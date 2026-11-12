"""Source-file aliases, so module and card files never carry real program or company names.

Files cite internal sources by alias  and write the program name as the
placeholder [ORG]. Nothing in this project maps an alias to a real document.

Optional private checks: set ENG_SOURCE_MAP to a JSON file kept OUTSIDE the project (default
~/.eng-training/source_map.json) with keys aliases, banned_names, placeholder, program_name and
source_dirs. When it is absent, quote checks against internal documents and the real-name scan
are skipped and the validators say so.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path

DEFAULT_MAP = Path.home() / ".eng-training" / "source_map.json"
ALIAS_RE = re.compile(r"^SRC-[A-Za-z0-9-]+$")
PLACEHOLDER = "[ORG]"


@lru_cache(maxsize=1)
def _load() -> dict:
    path = Path(os.environ.get("ENG_SOURCE_MAP", DEFAULT_MAP))
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def private_checks_available() -> bool:
    return bool(_load())


def source_dirs() -> list[Path]:
    """Folders holding the real documents; empty when no private map is configured."""
    data = _load()
    dirs = [data["primary_dir"]] if data.get("primary_dir") else []
    return [Path(d) for d in [*dirs, *data.get("source_dirs", [])]]


def banned_names() -> list[str]:
    return list(_load().get("banned_names", []))


def real_name(name: str) -> str:
    """Return the real file name for an alias; names that are not aliases pass through."""
    return _load().get("aliases", {}).get(name, name)


def unalias_quote(quote: str) -> str:
    """Put the real program name back into a quote so it can be matched against the source file."""
    data = _load()
    return quote.replace(PLACEHOLDER, data["program_name"]) if data.get("program_name") else quote


def is_internal_reference(name: str) -> bool:
    return bool(ALIAS_RE.match(name))


def display_name(name: str) -> str:
    """Readable label for a source: a hyphenated alias becomes spaced words. Other names are unchanged."""
    return name.replace("-", " ") if is_internal_reference(name) else name

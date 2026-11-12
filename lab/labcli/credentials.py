"""Per-lab random credentials for the in-lab services.

Generated once by `lab up` and kept only in the 0600 lab.env file. Nothing here
is a default, is written to Terraform state or outputs, or is printed.
"""
from __future__ import annotations

import os
import re
import secrets
from pathlib import Path

# Passwords the lab itself must create. GITEA_TOKEN and MM_WEBHOOK_URL are issued
# by Gitea and Mattermost when the lab build deploys them, so they cannot be
# generated here; the lab build writes them to lab.env (see LAB-CONTRACT.md).
GENERATED_VARS = ("KEYCLOAK_ADMIN_PASSWORD", "GRAFANA_PASSWORD", "LOKI_PASSWORD")
PASSWORD_BYTES = 24  # 32 URL-safe characters, 192 bits
_LINE = re.compile(r"^([A-Z][A-Z0-9_]*)=(.*)$")


def read_env_file(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    pairs = (_LINE.match(line) for line in text.splitlines())
    return {m.group(1): m.group(2) for m in pairs if m}


def with_generated(existing: dict[str, str]) -> dict[str, str]:
    """Return existing values plus a fresh random password for each missing one."""
    result = dict(existing)
    for name in GENERATED_VARS:
        if not result.get(name):
            result[name] = secrets.token_urlsafe(PASSWORD_BYTES)
    return result


def write_private(path: Path, text: str) -> None:
    """Write text to path, created with mode 0600 (no world-readable window)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)

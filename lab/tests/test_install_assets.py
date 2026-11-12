"""Static checks on the install template and script (no AWS)."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

TF = Path(__file__).resolve().parents[2] / "terraform"
TEMPLATE = TF / "templates" / "install-config.yaml.tpl"
SCRIPT = TF / "scripts" / "lab-install.sh"


def test_template_tokens_all_filled_by_script() -> None:
    tokens = set(re.findall(r"__[A-Z_]+__", TEMPLATE.read_text(encoding="ascii")))
    script = SCRIPT.read_text(encoding="ascii")
    assert tokens and all(f"{{CONFIG//{t}/" in script for t in tokens)


def test_template_required_settings() -> None:
    text = TEMPLATE.read_text(encoding="ascii")
    for needle in (
        "fips: true", "publish: External", "replicas: 1", "replicas: 0", "size: 120", "type: gp3",
        "kmsKeyARN", "additionalSecurityGroupIDs", "propagateUserTags: true", "LabId", "AutoDestroyAfter",
    ):
        assert needle in text


def test_template_holds_no_secret_lines() -> None:
    lines = [ln for ln in TEMPLATE.read_text(encoding="ascii").splitlines() if not ln.lstrip().startswith("#")]
    assert not any(ln.startswith(("pullSecret:", "sshKey:")) for ln in lines)


def test_script_never_prints_the_pull_secret() -> None:
    script = SCRIPT.read_text(encoding="ascii")
    assert "set -x" not in script
    assert not re.search(r"(say|echo)[^\n]*\$\{?PULL_SECRET\b", script)


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_script_syntax() -> None:
    done = subprocess.run(["bash", "-n"], input=SCRIPT.read_bytes(), check=False)
    assert done.returncode == 0

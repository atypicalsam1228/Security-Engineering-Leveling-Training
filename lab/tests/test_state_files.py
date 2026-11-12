"""Static checks on the real start states in lab/states (no cluster, no network).

They check file presence and order, shell and YAML syntax, idempotence markers, that scripts use only
LAB-CONTRACT variables and allowed tools, that images are pinned, that no start state already contains what
the module's own steps create, and that every module's lab_needs are accounted for in its TODO.md.
"""
from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from labcli.states import plan_state

ROOT = Path(__file__).resolve().parents[2]
STATES = ROOT / "lab" / "states"
GENERATORS = ROOT / "generators"
CONTRACT = ROOT / "LAB-CONTRACT.md"
COMMON = STATES / "_common"
RESET_DIR = "reset.d"
DOC_FILES = {"README.md", "TODO.md"}
# Modules whose own steps use the demo-app Deployment in namespace demo.
DEMO_APP_MODULES = ("eng-0", "grc-2", "grc-3", "grc-4", "grc-5")
# Start scripts run inside the tools container, which has python3, git, cosign and trivy; these are
# the tools it does not have, or that would reach outside the lab.
# terraform is in the lab image (IAC modules), so start scripts may call it.
FORBIDDEN_TOOLS = (
    "helm", "envsubst", "openssl", "docker", "podman", "yq", "skopeo", "gh", "kubectl",
)
SHELL_ALLOWED_NAMES = {"HOME", "PATH", "BASH_SOURCE"}


def _load_py(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _modules() -> list[dict]:
    """MODULE dicts for ids in generators/order.py that have a content file."""
    order_mod = _load_py(GENERATORS / "order.py", "state_test_order")
    found = []
    for module_id in order_mod.TRACK:
        path = GENERATORS / "content" / (module_id.lower().replace("-", "_") + ".py")
        if path.is_file():
            found.append(_load_py(path, "state_test_" + module_id.lower().replace("-", "_")).MODULE)
    return found


MODULES = _modules()
MODULE_IDS = [m["id"].lower() for m in MODULES]


def _state_files(include_common: bool = True) -> list[Path]:
    files = [p for p in STATES.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    if not include_common:
        files = [p for p in files if COMMON not in p.parents]
    return sorted(files)


def _scripts() -> list[Path]:
    return [p for p in _state_files() if p.suffix == ".sh"]


def _executable_lines(text: str) -> str:
    """Script text without comment lines, with backslash continuations joined."""
    lines = [l for l in text.splitlines() if not l.lstrip().startswith("#")]
    return re.sub(r"\\\n\s*", " ", "\n".join(lines))


def _non_reset_files(module: str) -> list[Path]:
    root = STATES / module
    return [p for p in root.rglob("*") if p.is_file() and RESET_DIR not in p.parts and p.name not in DOC_FILES]


# ---- presence, order -----------------------------------------------------------------------------

@pytest.mark.parametrize("module", MODULE_IDS)
def test_every_module_has_a_runnable_start_state(module: str) -> None:
    state = STATES / module
    assert (state / "README.md").is_file() and (state / "TODO.md").is_file()
    plan = plan_state(state, module, reset=False)
    assert not plan.missing and plan.steps, f"{module} has no start-state steps"


@pytest.mark.parametrize("module", MODULE_IDS)
def test_state_files_are_numbered(module: str) -> None:
    state = STATES / module
    for path in state.rglob("*"):
        # Only what `lab start` runs must be numbered: top-level or reset.d files that are scripts or manifests.
        # Helper kits in other subfolders, and files of other types, are copied by the start scripts.
        runs = path.parent in (state, state / RESET_DIR) and path.suffix in (".sh", ".yaml", ".yml", ".json")
        if path.is_file() and path.name not in DOC_FILES and runs:
            assert re.match(r"\d\d-[a-z0-9-]+\.(sh|yaml)$", path.name), f"bad file name {path}"


@pytest.mark.parametrize("module", MODULE_IDS)
def test_reset_runs_reset_files_before_start_files(module: str) -> None:
    names = [s.name for s in plan_state(STATES / module, module, reset=True).steps]
    resets = [i for i, n in enumerate(names) if n.startswith(RESET_DIR + "/")]
    starts = [i for i, n in enumerate(names) if not n.startswith(RESET_DIR + "/")]
    assert not resets or max(resets) < min(starts)


def test_no_state_directory_without_a_module() -> None:
    dirs = {p.name for p in STATES.iterdir() if p.is_dir() and p.name != "_common"}
    assert dirs <= set(MODULE_IDS), f"unknown state directories: {dirs - set(MODULE_IDS)}"


# ---- syntax ---------------------------------------------------------------------------------------

@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not installed")
@pytest.mark.parametrize("script", _scripts(), ids=lambda p: p.relative_to(STATES).as_posix())
def test_scripts_pass_bash_syntax_check(script: Path) -> None:
    # Relative name plus cwd: works with Git Bash, WSL bash and Linux alike.
    result = subprocess.run(["bash", "-n", script.name], cwd=script.parent, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("script", _scripts(), ids=lambda p: p.relative_to(STATES).as_posix())
def test_scripts_have_lf_endings_and_strict_mode(script: Path) -> None:
    raw = script.read_bytes()
    assert b"\r" not in raw
    text = raw.decode("utf-8")
    assert text.startswith("#!/usr/bin/env bash")
    if script.name != "lib.sh":
        # Cleanup scripts under reset.d keep going after one failed delete, so they may omit -e.
        accepted = ("set -euo pipefail", "set -uo pipefail") if RESET_DIR in script.parts else ("set -euo pipefail",)
        assert any(a in text for a in accepted)


@pytest.mark.parametrize("path", [p for p in _state_files() if p.suffix in (".yaml", ".yml")],
                         ids=lambda p: p.relative_to(STATES).as_posix())
def test_yaml_files_are_valid(path: Path) -> None:
    docs = [d for d in yaml.safe_load_all(path.read_text(encoding="utf-8")) if d is not None]
    assert docs
    assert all(isinstance(d, dict) and "kind" in d for d in docs)


# ---- idempotence markers and allowed tools ------------------------------------------------------

@pytest.mark.parametrize("script", _scripts(), ids=lambda p: p.relative_to(STATES).as_posix())
def test_creates_and_deletes_are_safe_to_repeat(script: Path) -> None:
    body = _executable_lines(script.read_text(encoding="utf-8"))
    for line in body.splitlines():
        if re.search(r"\boc create (?!token)", line):
            assert "--dry-run=client" in line or " || " in line, f"bare create: {line.strip()}"
        if re.search(r"\boc delete\b", line):
            assert "--ignore-not-found" in line, f"delete without --ignore-not-found: {line.strip()}"
        if re.search(r"\boc adm policy add-", line):
            pytest.fail(f"use a dry-run create and apply instead of: {line.strip()}")


@pytest.mark.parametrize("script", _scripts(), ids=lambda p: p.relative_to(STATES).as_posix())
def test_scripts_use_only_allowed_tools(script: Path) -> None:
    body = _executable_lines(script.read_text(encoding="utf-8"))
    pattern = r"(?:^|[|;&(]|\$\()\s*(" + "|".join(FORBIDDEN_TOOLS) + r")\s"
    assert not re.search(pattern, body, flags=re.M), f"forbidden tool in {script.name}"


def _contract_vars() -> set[str]:
    line = next(l for l in CONTRACT.read_text(encoding="utf-8").splitlines() if l.startswith("VARS:"))
    return set(line.split(":", 1)[1].split())


def _assigned_names(text: str) -> set[str]:
    names = set(re.findall(r"(?m)^\s*(?:local\s+|export\s+)?([A-Z][A-Z0-9_]*)=", text))
    names |= set(re.findall(r"\bfor ([A-Z][A-Z0-9_]*) in\b", text))
    return names


@pytest.mark.parametrize("path", [p for p in _state_files() if p.suffix in (".sh", ".yaml")],
                         ids=lambda p: p.relative_to(STATES).as_posix())
def test_only_contract_variables_are_used(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    known = _contract_vars() | SHELL_ALLOWED_NAMES | _assigned_names(text)
    known |= _assigned_names((COMMON / "lib.sh").read_text(encoding="utf-8"))
    used = set(re.findall(r"\$\{?([A-Z][A-Z0-9_]*)", _executable_lines(text)))
    assert used <= known, f"{path.name} uses variables outside LAB-CONTRACT.md: {sorted(used - known)}"


def test_contract_variables_reach_the_container() -> None:
    from labcli.environment import CONTRACT_VARS

    assert _contract_vars() <= set(CONTRACT_VARS)


# ---- images and demo-app -----------------------------------------------------------------------

def _image_refs(path: Path) -> list[str]:
    return re.findall(r"(?m)^\s*(?:-\s*)?image:\s*['\"]?([^\s'\"]+)", path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", [p for p in _state_files() if p.suffix in (".yaml", ".sh")],
                         ids=lambda p: p.relative_to(STATES).as_posix())
def test_image_references_are_pinned(path: Path) -> None:
    for image in _image_refs(path):
        if image.startswith("$"):
            continue
        assert "@sha256:" in image or (":" in image.rsplit("/", 1)[-1] and not image.endswith(":latest")), image


def test_demo_app_manifest() -> None:
    docs = list(yaml.safe_load_all((COMMON / "demo-app.yaml").read_text(encoding="utf-8")))
    kinds = {d["kind"]: d for d in docs}
    deploy = kinds["Deployment"]
    assert deploy["metadata"]["name"] == "demo-app" and deploy["metadata"]["namespace"] == "demo"
    assert kinds["Namespace"]["metadata"]["name"] == "demo"
    assert kinds["ServiceAccount"]["metadata"]["name"] == "demo-app"
    pod = deploy["spec"]["template"]
    assert pod["metadata"]["labels"]["app"] == "demo-app"
    assert pod["spec"]["serviceAccountName"] == "demo-app"
    assert pod["spec"]["securityContext"]["runAsNonRoot"] is True
    container = pod["spec"]["containers"][0]
    assert container["name"] == "demo-app"
    assert container["image"].startswith("registry.access.redhat.com/ubi9/ubi-minimal:")
    assert not container["image"].endswith(":latest")
    assert deploy["spec"]["replicas"] == 1


@pytest.mark.parametrize("module", DEMO_APP_MODULES)
def test_modules_that_use_demo_app_provide_it(module: str) -> None:
    text = "\n".join(p.read_text(encoding="utf-8") for p in _non_reset_files(module))
    assert "ensure_demo_app" in text


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not installed")
@pytest.mark.parametrize("exists", [True, False])
def test_ensure_demo_app_applies_only_when_missing(tmp_path: Path, exists: bool) -> None:
    common = tmp_path / "common"
    common.mkdir()
    for name in ("lib.sh", "demo-app.yaml"):
        shutil.copyfile(COMMON / name, common / name)
    fake_oc = (
        'oc() { echo "$*" >> calls.txt; '
        f'if [ "$1 $2" = "get deployment" ]; then {"true" if exists else "false"}; fi; }}'
    )
    # Run from a file, not bash -c: a launcher such as wsl.exe would expand the dollar signs itself.
    script = "\n".join([fake_oc, ". ./common/lib.sh", "ensure_demo_app", "ensure_demo_app"]) + "\n"
    (tmp_path / "run.sh").write_text(script, encoding="utf-8", newline="\n")
    result = subprocess.run(["bash", "run.sh"], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    calls = (tmp_path / "calls.txt").read_text(encoding="utf-8")
    assert ("apply -f" in calls) is (not exists)
    assert calls.count("rollout status deployment/demo-app") == 2


# ---- lab_needs coverage ------------------------------------------------------------------------

NEED_LINE = re.compile(r"(?m)^[+-] \[(done|live|lab-build)\] (\d+): \S")


@pytest.mark.parametrize("module", MODULES, ids=lambda m: m["id"])
def test_every_lab_need_is_accounted_for_in_todo(module: dict) -> None:
    needs = module.get("lab_needs") or []
    if not needs:
        pytest.skip("the learner format no longer lists lab_needs")
    todo = (STATES / module["id"].lower() / "TODO.md").read_text(encoding="utf-8")
    accounted = {int(n) for _, n in NEED_LINE.findall(todo)}
    assert accounted == set(range(1, len(needs) + 1)), f"{module['id']}: TODO.md covers {sorted(accounted)} of {len(needs)} needs"


@pytest.mark.parametrize("module", MODULE_IDS)
def test_done_lines_use_plus_and_open_lines_use_dash(module: str) -> None:
    todo = (STATES / module / "TODO.md").read_text(encoding="utf-8")
    for line in todo.splitlines():
        if re.match(r"[+-] \[", line):
            assert line.startswith("+ [done]") or line.startswith(("- [live]", "- [lab-build]")), line


@pytest.mark.parametrize("module", MODULE_IDS)
def test_readme_describes_what_is_implemented(module: str) -> None:
    readme = (STATES / module / "README.md").read_text(encoding="utf-8")
    assert "Implemented: " in readme and "Implemented: Nothing yet." not in readme

"""The tools image definition must cover every in-container tool the modules call."""
from __future__ import annotations

import io
import re
from pathlib import Path

from conftest import FakeRunner
from labcli.cli import Deps, main
from labcli.environment import DEFAULT_IMAGE

LAB = Path(__file__).resolve().parents[1]
IMAGE = LAB / "image"
COMMANDS = LAB.parent / "generators" / "checks" / "commands.txt"

# Tokens in commands.txt that are shell keywords/builtins, host-side, or run elsewhere.
NOT_IN_CONTAINER = {
    "lab", "docker", "podman",
    "for", "while", "break", "env", "cd", "export", "read", "exit", "clear",
    "mkrule", "mkrule()", "note", "note()", "python", "pip", "kill",
}
# Core tools from the base image (coreutils-single, grep, sed, bash): named in versions.txt as groups.
BASE_IMAGE_TOOLS = {
    "echo", "cat", "sleep", "date", "grep", "sed", "head", "tail", "wc", "sort", "uniq", "tr",
    "cut", "printf", "mkdir", "ls", "test", "chmod", "base64", "true", "false", "uname", "df",
    "pwd", "whoami", "env", "touch", "cp", "tee", "timeout", "bash",
}


def _tokens() -> set[str]:
    return set(COMMANDS.read_text(encoding="utf-8").split())


def _text() -> str:
    return (IMAGE / "Dockerfile").read_text(encoding="utf-8") + (IMAGE / "versions.txt").read_text(encoding="utf-8")


def test_every_expected_command_is_in_dockerfile_or_versions() -> None:
    text = _text()
    missing = [
        t for t in sorted(_tokens() - NOT_IN_CONTAINER)
        if not re.search(rf"(?<![A-Za-z0-9_-]){re.escape(t)}(?![A-Za-z0-9_-])", text)
    ]
    assert not missing, f"tools used by modules but absent from image files: {missing}"


def test_contract_tools_are_in_versions() -> None:
    contract = (LAB.parent / "LAB-CONTRACT.md").read_text(encoding="utf-8")
    line = next(l for l in contract.splitlines() if l.startswith("Learners run every command"))
    listed = re.search(r"It has: (.*)\.$", line).group(1).split(", ")
    versions = (IMAGE / "versions.txt").read_text(encoding="utf-8")
    missing = [t for t in listed if t.split(" (")[0] not in versions]
    assert not missing, f"contract tools missing from versions.txt: {missing}"


def test_every_downloaded_file_has_a_pinned_checksum() -> None:
    sums = (IMAGE / "checksums.sha256").read_text(encoding="utf-8").splitlines()
    assert all(re.fullmatch(r"[0-9a-f]{64}  \S+", line) for line in sums)
    names = " ".join(line.split()[1] for line in sums)
    for arch in ("amd64", "arm64"):
        assert f"terraform_1.17.0_linux_{arch}.zip" in names
        assert f"cosign-linux-{arch}" in names


def test_dockerfile_non_root_and_no_secrets() -> None:
    dockerfile = (IMAGE / "Dockerfile").read_text(encoding="utf-8")
    assert re.search(r"^USER 1001$", dockerfile, re.M)
    assert not re.search(r"^\s*ENV .*(PASSWORD|TOKEN|SECRET|ACCESS_KEY)", dockerfile, re.M)
    assert DEFAULT_IMAGE.split(":")[0] in (IMAGE / "README.md").read_text(encoding="utf-8")


def test_image_files_are_ascii() -> None:
    for path in IMAGE.iterdir():
        if path.suffix in {"", ".txt", ".sha256", ".md", ".sh", ".ps1"} or path.name == "Dockerfile":
            path.read_bytes().decode("ascii")


def test_build_image_dry_run_uses_default_image(tmp_path) -> None:
    out = io.StringIO()
    runner = FakeRunner()
    deps = Deps(runner=runner, out=out, ask=lambda p: "", which=lambda n: f"/bin/{n}", environ={})
    assert main(["build-image", "--dry-run"], deps) == 0
    assert DEFAULT_IMAGE in out.getvalue() and "Dockerfile" in out.getvalue()
    assert runner.calls == []


def test_build_image_runs_and_reports_failure() -> None:
    class Failing(FakeRunner):
        def run_interactive(self, argv):
            self.calls.append(tuple(argv))
            return 1

    out = io.StringIO()
    runner = Failing()
    deps = Deps(runner=runner, out=out, ask=lambda p: "", which=lambda n: f"/bin/{n}", environ={"LAB_ENGINE": "docker"})
    assert main(["build-image"], deps) == 1
    assert runner.calls[0][:2] == ("docker", "build")

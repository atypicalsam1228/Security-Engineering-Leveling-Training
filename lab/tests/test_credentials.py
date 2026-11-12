from __future__ import annotations

from pathlib import Path

from labcli.credentials import GENERATED_VARS, read_env_file, with_generated, write_private


def test_generates_every_missing_password_and_they_differ() -> None:
    result = with_generated({"KMS_KEY_ARN": "arn:k"})
    values = [result[name] for name in GENERATED_VARS]
    assert all(len(v) >= 32 for v in values)
    assert len(set(values)) == len(values)
    assert with_generated({}) != result  # random per call


def test_existing_credentials_are_kept() -> None:
    result = with_generated({"LOKI_PASSWORD": "kept-value"})
    assert result["LOKI_PASSWORD"] == "kept-value"


def test_write_private_and_read_back(tmp_path: Path) -> None:
    path = tmp_path / ".lab" / "lab.env"
    write_private(path, "A=b\nBAD LINE\nC=d=e\n")
    assert read_env_file(path) == {"A": "b", "C": "d=e"}
    assert read_env_file(tmp_path / "missing") == {}


def test_no_default_password_in_source() -> None:
    src = (Path(__file__).parent.parent / "labcli" / "credentials.py").read_text(encoding="utf-8")
    assert "admin123" not in src and "changeme" not in src.lower()

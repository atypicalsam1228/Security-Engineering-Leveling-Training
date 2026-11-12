from __future__ import annotations

from pathlib import Path

import pytest

from labcli.catalog import UnknownModuleError, load_catalog, normalize_id

REAL_GEN = Path(__file__).resolve().parents[2] / "generators"


def test_loads_in_order(gen_dir: Path) -> None:
    catalog = load_catalog(gen_dir)
    assert [m.id for m in catalog.modules] == ["ENG-0", "GRC-2"]
    assert catalog.modules[1].position == 2


def test_module_fields(gen_dir: Path) -> None:
    mod = load_catalog(gen_dir).get("grc-2")
    assert mod.title == "Title GRC-2"
    assert mod.env == ("LOKI_URL", "LOKI_PASSWORD")
    assert mod.needs == ("need one",)
    assert mod.state_name == "grc-2"
    assert mod.minutes == 55


def test_unknown_module(gen_dir: Path) -> None:
    with pytest.raises(UnknownModuleError):
        load_catalog(gen_dir).get("nope")


def test_normalize_id() -> None:
    assert normalize_id(" grc-2 ") == "GRC-2"
    assert normalize_id("eng-0") == "ENG-0"


def test_missing_content_file(gen_dir: Path) -> None:
    (gen_dir / "content" / "eng_0.py").unlink()
    with pytest.raises(ValueError, match="ENG-0"):
        load_catalog(gen_dir)


def test_missing_generators_dir(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="order.py"):
        load_catalog(tmp_path / "absent")


def test_id_mismatch(gen_dir: Path) -> None:
    path = gen_dir / "content" / "eng_0.py"
    path.write_text(path.read_text(encoding="utf-8").replace('"id": "ENG-0"', '"id": "X"'), encoding="utf-8")
    with pytest.raises(ValueError, match="mismatch"):
        load_catalog(gen_dir)


@pytest.mark.skipif(not REAL_GEN.exists(), reason="real generators not present")
def test_real_catalog() -> None:
    catalog = load_catalog(REAL_GEN)
    assert len(catalog.modules) == 29
    assert catalog.modules[0].id == "ENG-0"


@pytest.mark.skipif(not REAL_GEN.exists(), reason="real generators not present")
def test_track_has_29_unique_modules() -> None:
    modules = load_catalog(REAL_GEN).modules
    assert len(modules) == 29
    assert len({m.id for m in modules}) == len(modules)

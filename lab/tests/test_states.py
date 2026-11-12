from __future__ import annotations

from pathlib import Path

from labcli.states import plan_state


def build(tmp_path: Path) -> Path:
    d = tmp_path / "vm-2"
    (d / "reset.d").mkdir(parents=True)
    (d / "20-b.sh").write_text("true", encoding="utf-8")
    (d / "10-a.yaml").write_text("kind: x", encoding="utf-8")
    (d / "README.md").write_text("r", encoding="utf-8")
    (d / "TODO.md").write_text("need", encoding="utf-8")
    (d / "reset.d" / "05-x.sh").write_text("true", encoding="utf-8")
    return d


def test_plan_orders_and_classifies(tmp_path: Path) -> None:
    plan = plan_state(build(tmp_path), "vm-2", reset=False)
    assert [s.name for s in plan.steps] == ["10-a.yaml", "20-b.sh"]
    assert plan.steps[0].argv == ("oc", "apply", "-f", "/lab/states/vm-2/10-a.yaml")
    assert plan.steps[1].argv == ("bash", "/lab/states/vm-2/20-b.sh")
    assert plan.todo == "need"


def test_plan_reset_runs_reset_first(tmp_path: Path) -> None:
    plan = plan_state(build(tmp_path), "vm-2", reset=True)
    assert [s.name for s in plan.steps] == ["reset.d/05-x.sh", "10-a.yaml", "20-b.sh"]
    assert plan.steps[0].argv == ("bash", "/lab/states/vm-2/reset.d/05-x.sh")


def test_plan_missing_dir(tmp_path: Path) -> None:
    plan = plan_state(tmp_path / "none", "zz", reset=False)
    assert plan.steps == () and plan.missing


def test_unknown_extension_ignored(tmp_path: Path) -> None:
    d = tmp_path / "m"
    d.mkdir()
    (d / "10-a.txt").write_text("x", encoding="utf-8")
    assert plan_state(d, "m", reset=False).steps == ()

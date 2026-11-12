"""Per-module commands: modules, start, reset."""
from __future__ import annotations

import json
from argparse import Namespace
from datetime import datetime, timezone

from labcli.catalog import UnknownModuleError
from labcli.commands_fault import active_faults
from labcli.redact import redact
from labcli.context import EXIT_FAIL, EXIT_OK, EXIT_USAGE, Ctx, engine_or_none
from labcli.models import ModuleSpec
from labcli.states import Step, plan_state

MODULES_FILE = "modules.json"
TODO_PREVIEW_LINES = 12


def cmd_modules(ctx: Ctx, args: Namespace) -> int:
    catalog = ctx.catalog()
    ctx.say(f"{'#':>2}  {'ID':<7} {'Min':>3}  Title")
    for m in catalog.modules:
        tag = "  (optional)" if m.optional else ""
        ctx.say(f"{m.position:>2}  {m.id:<7} {m.minutes:>3}  {m.title}{tag}")
    return EXIT_OK


def _lookup(ctx: Ctx, raw: str) -> ModuleSpec | None:
    try:
        return ctx.catalog().get(raw)
    except UnknownModuleError as err:
        ctx.say(f"ERROR: {err.args[0]}")
        return None


def _record(ctx: Ctx, module: ModuleSpec, action: str) -> None:
    path = ctx.workspace / ".lab" / MODULES_FILE
    try:
        current = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        current = {}
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    updated = {**current, module.id: {"action": action, "at": stamp}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(updated, indent=2), encoding="utf-8")


def _print_todo(ctx: Ctx, todo: str) -> None:
    ctx.say("INCOMPLETE: this start state is only partly built. Still needed (see states/<module>/TODO.md):")
    items = [l for l in todo.strip().splitlines() if l.startswith("- ")]
    for line in items[:TODO_PREVIEW_LINES]:
        ctx.say("  " + line[:200])


def _apply_steps(ctx: Ctx, module: ModuleSpec, steps: tuple[Step, ...]) -> bool:
    env = engine_or_none(ctx)
    if env is None:
        return False
    for step in steps:
        ctx.say(f"  applying {step.name}")
        try:
            result = ctx.deps.runner.run(env.wrap(step.argv, states=True))
        except OSError as err:
            ctx.say(f"ERROR: cannot run {step.name}: {err}")
            return False
        if result.returncode != 0:
            ctx.say(f"ERROR: {step.name} failed (exit {result.returncode}):")
            ctx.say(redact(result.output, ctx.secrets()).strip())
            return False
    return True


def _run_state(ctx: Ctx, args: Namespace, reset: bool) -> int:
    module = _lookup(ctx, args.module)
    if module is None:
        return EXIT_USAGE
    action = "reset" if reset else "start"
    plan = plan_state(ctx.lab_states_dir() / module.state_name, module.state_name, reset)
    if plan.missing:
        ctx.say(f"No start state for {module.id} yet (states/{module.state_name}/ not found).")
        return EXIT_FAIL
    ctx.say(f"{action} {module.id}: {module.title}")
    for fault_module, ids in active_faults(ctx).items():
        ctx.say(f"NOTE: {fault_module} faults still active ({', '.join(ids)}). They may affect this module. Undo with: lab restore {fault_module.lower()} --all")
    if module.prereq:
        ctx.say("Prerequisites: " + "; ".join(module.prereq))
    if not plan.steps:
        _print_todo(ctx, plan.todo)
        return EXIT_FAIL
    if args.dry_run:
        for step in plan.steps:
            ctx.say(f"  would apply {step.name}: " + " ".join(step.argv))
    elif not _apply_steps(ctx, module, plan.steps):
        return EXIT_FAIL
    else:
        _record(ctx, module, action)
    if any(line.startswith("- ") for line in plan.todo.splitlines()):
        _print_todo(ctx, plan.todo)
    return EXIT_OK


def cmd_start(ctx: Ctx, args: Namespace) -> int:
    return _run_state(ctx, args, reset=False)


def cmd_reset(ctx: Ctx, args: Namespace) -> int:
    return _run_state(ctx, args, reset=True)

"""Fault practice commands: break and restore named, reversible faults for a module."""
from __future__ import annotations

import json
from argparse import Namespace

from labcli.catalog import UnknownModuleError
from labcli.redact import redact
from labcli.context import EXIT_FAIL, EXIT_OK, EXIT_USAGE, Ctx, engine_or_none
from labcli.models import Fault, ModuleSpec

FAULTS_FILE = "faults.json"


def _record_path(ctx: Ctx):
    return ctx.workspace / ".lab" / FAULTS_FILE


def _read_active(ctx: Ctx) -> dict[str, list[str]]:
    try:
        return json.loads(_record_path(ctx).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def active_faults(ctx: Ctx) -> dict[str, list[str]]:
    """Modules that still have a fault applied, mapped to the fault ids."""
    return {module: ids for module, ids in _read_active(ctx).items() if ids}


def _write_active(ctx: Ctx, module: ModuleSpec, active: list[str]) -> None:
    path = _record_path(ctx)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({**_read_active(ctx), module.id: active}, indent=2), encoding="utf-8")


def _list(ctx: Ctx, module: ModuleSpec) -> None:
    active = _read_active(ctx).get(module.id, [])
    ctx.say(f"Faults for {module.id}:")
    for fault in module.faults:
        flag = "ACTIVE" if fault.id in active else "      "
        ctx.say(f"  {fault.id:<14} {flag}  {fault.title}")
    ctx.say(f"Apply one: lab break {module.id.lower()} <fault>. Apply all: lab break {module.id.lower()} --all")


def _select(ctx: Ctx, module: ModuleSpec, args: Namespace) -> tuple[Fault, ...] | None:
    if args.all:
        return module.faults
    if not args.fault:
        ctx.say(f"ERROR: name a fault or use --all. Run 'lab break {module.id.lower()} --list' to see them.")
        return None
    chosen = tuple(f for f in module.faults if f.id == args.fault)
    if not chosen:
        ctx.say(f"ERROR: unknown fault '{args.fault}' for {module.id}.")
        _list(ctx, module)
        return None
    return chosen


def _run(ctx: Ctx, code: str, label: str) -> bool:
    env = engine_or_none(ctx)
    if env is None:
        return False
    try:
        result = ctx.deps.runner.run(env.wrap(("bash", "-c", code)))
    except OSError as err:
        ctx.say(f"ERROR: cannot run {label}: {err}")
        return False
    shown = redact(result.output, ctx.secrets()).strip()
    if result.returncode != 0:
        ctx.say(f"ERROR: {label} failed (exit {result.returncode}). Nothing was recorded for it:")
        ctx.say(shown)
        return False
    if shown:
        ctx.say(shown)
    return True


def _apply(ctx: Ctx, args: Namespace, restore: bool) -> int:
    try:
        module = ctx.catalog().get(args.module)
    except UnknownModuleError as err:
        ctx.say(f"ERROR: {err.args[0]}")
        return EXIT_USAGE
    if not module.faults:
        ctx.say(f"{module.id} has no faults to practice.")
        return EXIT_USAGE
    if args.list:
        _list(ctx, module)
        return EXIT_OK
    chosen = _select(ctx, module, args)
    if chosen is None:
        return EXIT_USAGE
    active = list(_read_active(ctx).get(module.id, []))
    for fault in chosen:
        code = fault.restore_code if restore else fault.break_code
        verb = "restore" if restore else "break"
        ctx.say(f"{verb} {module.id}: {fault.id} - {fault.title}")
        if args.dry_run:
            ctx.say("\n".join("    " + line for line in code.splitlines()))
            continue
        if not _run(ctx, code, f"{verb} {fault.id}"):
            return EXIT_FAIL
        active = [i for i in active if i != fault.id] + ([] if restore else [fault.id])
        _write_active(ctx, module, active)
        if not restore:
            ctx.say(f"Applied. Follow the detection path for '{fault.id}' in the module, then run: lab restore {module.id.lower()} {fault.id}")
    return EXIT_OK


def cmd_break(ctx: Ctx, args: Namespace) -> int:
    return _apply(ctx, args, restore=False)


def cmd_restore(ctx: Ctx, args: Namespace) -> int:
    return _apply(ctx, args, restore=True)

"""Cost guard commands: keep, pause, resume, pull, and the status line."""
from __future__ import annotations

import re
from argparse import Namespace
from datetime import timedelta

from labcli.context import EXIT_FAIL, EXIT_OK, EXIT_USAGE, Ctx
from labcli.commands_lab import _lifecycle_env
from labcli.environment import CONTAINER_WORKSPACE, LabEnv
from labcli.guard import (
    AWS_TIMEOUT_SECONDS,
    BILLING_NOTE,
    DEFAULT_IDLE_HOURS,
    KEEP_DEFAULT_HOURS,
    KEEP_MAX_HOURS,
    SAVE_NAME_PATTERN,
    GuardSettings,
    get_json,
    iso,
    parse_iso,
    pause_estimate,
    put_json,
    read_local,
    resolve_settings,
    wake_guard,
    update_local,
    write_heartbeat,
)
from labcli.redact import redact

POLL_SECONDS = 30.0
POLL_LIMIT_SECONDS = 30 * 60.0
TARGET_STATUS = {"pause": "paused", "resume": "running"}
ALREADY = {"pause": ("paused", "pausing", "saving"), "resume": ("running", "warned", "resuming")}
GONE = ("destroying", "destroyed")
_PRE_LINE = re.compile(r"^\s*PRE\s+(\S+?)/\s*$")


def _prepare(ctx: Ctx) -> tuple[LabEnv, GuardSettings] | None:
    """Common start for guard commands that run from the learner's own computer."""
    env = _lifecycle_env(ctx)
    if env is None:
        return None
    settings = resolve_settings(ctx)
    return None if settings is None else (env, settings)


def cmd_keep(ctx: Ctx, args: Namespace) -> int:
    hours = KEEP_DEFAULT_HOURS if args.hours is None else args.hours
    if not 1 <= hours <= KEEP_MAX_HOURS:
        raise ValueError(f"HOURS must be a whole number from 1 to {KEEP_MAX_HOURS}.")
    prepared = _prepare(ctx)
    if prepared is None:
        return EXIT_USAGE
    env, settings = prepared
    until = iso(ctx.deps.now() + timedelta(hours=hours))
    key = f"keep/{settings.lab_id}"
    if args.dry_run:
        ctx.say(f"Would write {key} (until {until}) to the guard bucket.")
        return EXIT_OK
    error = put_json(ctx, env, settings.bucket, key, {"until": until})
    if error:
        ctx.say(f"Could not extend your lab: {error}")
        return EXIT_FAIL
    update_local(env, keep_until=until)
    ctx.say(f"Your lab will not be paused for idleness until {until} ({hours} hours). {BILLING_NOTE}")
    return EXIT_OK


def _state(ctx: Ctx, env: LabEnv, settings: GuardSettings) -> dict | None:
    return get_json(ctx, env, settings.bucket, f"state/{settings.lab_id}.json")


def _wait_for(ctx: Ctx, env: LabEnv, settings: GuardSettings, action: str) -> int:
    target = TARGET_STATUS[action]
    waited = 0.0
    last = ""
    while waited <= POLL_LIMIT_SECONDS:
        state = _state(ctx, env, settings)
        status = str(state.get("status", "")) if state else ""
        if status != last:
            ctx.say(f"  state: {status or 'not reported yet'}")
            last = status
        if status == target:
            ctx.say(f"Done: your lab is {target}.")
            return EXIT_OK
        if status in GONE or status == "error":
            detail = redact(str(state.get("last_error", "")), ctx.secrets()) if state else ""
            ctx.say(f"The guard reports '{status}'. {detail} Check 'lab status'. {BILLING_NOTE}")
            return EXIT_FAIL
        ctx.deps.sleep(POLL_SECONDS)
        waited += POLL_SECONDS
    ctx.say(
        f"Still not {target} after {int(POLL_LIMIT_SECONDS // 60)} minutes. The request stays queued; "
        f"run 'lab status' later. {BILLING_NOTE}"
    )
    return EXIT_FAIL


def _request(ctx: Ctx, args: Namespace, action: str) -> int:
    prepared = _prepare(ctx)
    if prepared is None:
        return EXIT_USAGE
    env, settings = prepared
    key = f"requests/{settings.lab_id}.json"
    if args.dry_run:
        ctx.say(f"Would write {key} with action '{action}' to the guard bucket.")
        return EXIT_OK
    state = _state(ctx, env, settings)
    status = str(state.get("status", "")) if state else ""
    if status in GONE:
        ctx.say(f"Your lab is {status}; there is nothing to {action}. {BILLING_NOTE}")
        return EXIT_FAIL
    if status in ALREADY[action]:
        ctx.say(f"Your lab is already {status}; no request sent. {BILLING_NOTE}")
        return EXIT_OK
    error = put_json(ctx, env, settings.bucket, key, {"action": action, "ts": iso(ctx.deps.now())})
    if error:
        ctx.say(f"Could not send the {action} request: {error}")
        return EXIT_FAIL
    if wake_guard(ctx, env):
        ctx.say(f"{action.capitalize()} requested. The guard was woken and is acting now. {BILLING_NOTE}")
    else:
        ctx.say(f"{action.capitalize()} requested. The guard checks about every 15 minutes. {BILLING_NOTE}")
    if action == "resume":
        beat_error = write_heartbeat(ctx, env, settings)
        if beat_error:
            ctx.say(f"Note: heartbeat not written: {beat_error}")
    if args.no_wait:
        ctx.say("Not waiting (--no-wait). Run 'lab status' to follow progress.")
        return EXIT_OK
    return _wait_for(ctx, env, settings, action)


def cmd_pause(ctx: Ctx, args: Namespace) -> int:
    return _request(ctx, args, "pause")


def cmd_resume(ctx: Ctx, args: Namespace) -> int:
    return _request(ctx, args, "resume")


def _list_saves(ctx: Ctx, env: LabEnv, settings: GuardSettings) -> list[str] | None:
    """Save names, oldest first, or None if the listing failed."""
    argv = ("aws", "s3", "ls", f"s3://{settings.bucket}/saves/{settings.lab_id}/", "--only-show-errors")
    result = ctx.deps.runner.run(env.wrap(argv), AWS_TIMEOUT_SECONDS)
    if result.returncode != 0:
        ctx.say("Could not list saves: " + redact(result.output.strip() or "aws failed", ctx.secrets()))
        return None
    found = (_PRE_LINE.match(line) for line in result.output.splitlines())
    return sorted(m.group(1) for m in found if m and SAVE_NAME_PATTERN.match(m.group(1)))


def _copy_save(ctx: Ctx, env: LabEnv, settings: GuardSettings, name: str) -> int:
    host = ctx.workspace / "saves" / name
    seen = host.as_posix() if env.in_shell else f"{CONTAINER_WORKSPACE}/saves/{name}"
    source = f"s3://{settings.bucket}/saves/{settings.lab_id}/{name}/"
    host.mkdir(parents=True, exist_ok=True)
    argv = ("aws", "s3", "cp", "--recursive", "--only-show-errors", source, seen)
    result = ctx.deps.runner.run(env.wrap(argv), AWS_TIMEOUT_SECONDS * 5)
    if result.returncode != 0:
        ctx.say("Copy failed: " + redact(result.output.strip() or "aws failed", ctx.secrets()))
        return EXIT_FAIL
    ctx.say(f"Saved copy: {host}")
    ctx.say("It holds git bundles, namespace YAML (no Secrets), MANIFEST.json and restore.sh.")
    return EXIT_OK


def cmd_pull(ctx: Ctx, args: Namespace) -> int:
    prepared = _prepare(ctx)
    if prepared is None:
        return EXIT_USAGE
    env, settings = prepared
    if args.dry_run:
        ctx.say(f"Would list s3://{settings.bucket}/saves/{settings.lab_id}/ and copy the newest save.")
        return EXIT_OK
    saves = _list_saves(ctx, env, settings)
    if saves is None:
        return EXIT_FAIL
    if args.list:
        ctx.say("Available saves (oldest first):" if saves else "No saves yet. The guard saves before it pauses.")
        for name in saves:
            ctx.say(f"  {name}")
        return EXIT_OK
    if not saves:
        ctx.say("No saves yet. The guard saves your lab files before it pauses or destroys it.")
        return EXIT_FAIL
    return _copy_save(ctx, env, settings, saves[-1])


def _age_text(delta: timedelta) -> str:
    minutes = max(int(delta.total_seconds() // 60), 0)
    hours, rest = divmod(minutes, 60)
    return f"{hours}h {rest}m" if hours else f"{rest}m"


def guard_status_lines(ctx: Ctx) -> list[str]:
    """Guard section of `lab status`; never raises."""
    settings = resolve_settings(ctx, say=False)
    if settings is None:
        reason = "GUARD_BUCKET is not set" if not ctx.deps.environ.get("GUARD_BUCKET") else "check GUARD_BUCKET and LAB_ID"
        return [f"Guard: not configured ({reason}). " + BILLING_NOTE]
    try:
        env = ctx.lab_env()
    except RuntimeError:
        return ["Guard: configured, but the state cannot be read without podman or docker."]
    state = _state(ctx, env, settings)
    status = str(state.get("status", "unknown")) if state else None
    lines = [f"Guard state: {status} (since {state.get('since', '?')})" if state else "Guard state: not reported yet"]
    now = ctx.deps.now()
    local = read_local(env)
    beat = parse_iso(local.get("heartbeat"))
    lines.append("Last heartbeat from this computer: " + (_age_text(now - beat) + " ago" if beat else "none"))
    if status in (None, "running", "warned"):
        left = pause_estimate(local, now)
        if left is not None and left.total_seconds() > 0:
            lines.append(
                f"Pause in about {_age_text(left)} unless you run 'lab keep' "
                f"(estimate; assumes {DEFAULT_IDLE_HOURS} idle hours)"
            )
        elif left is not None:
            lines.append("Pause is due at the guard's next check unless you run 'lab keep'.")
    lines.append(BILLING_NOTE)
    return lines

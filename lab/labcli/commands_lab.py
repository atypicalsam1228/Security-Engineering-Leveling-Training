"""Commands that act on the whole lab: shell, up, down, status."""
from __future__ import annotations

import json
import os
from argparse import Namespace
from pathlib import Path

from labcli.commands_fault import active_faults
from labcli.credentials import read_env_file, with_generated, write_private
from labcli.context import EXIT_FAIL, EXIT_OK, EXIT_USAGE, Ctx, engine_or_none
from labcli.guard import Heartbeat, resolve_settings, write_heartbeat
from labcli.environment import (
    CONTRACT_VARS,
    INSTALL_FILE_VARS,
    INSTALL_PASSTHROUGH,
    EngineNotFoundError,
    LabEnv,
    detect_engine,
    workspace_container_path,
)
from labcli.terraform import (
    CLUSTER_DESTROY_FAILED,
    CLUSTER_FAILED,
    COST_WARNING,
    DESTROY_WARNING,
    DOWN_FAILED,
    PULL_SECRET_HELP,
    apply_argv,
    cluster_destroy_argv,
    destroy_argv,
    init_argv,
    install_argv,
    output_argv,
    outputs_to_env,
    platform_argv,
)

CONFIRM_UP = "yes"
CONFIRM_DOWN = "destroy"
MODULES_FILE = "modules.json"


def cmd_shell(ctx: Ctx, args: Namespace) -> int:
    if ctx.in_shell:
        ctx.say("You are already inside the lab shell.")
        return EXIT_USAGE
    env = engine_or_none(ctx)
    if env is None:
        return EXIT_USAGE
    argv = env.shell_argv()
    if args.dry_run:
        ctx.show(argv)
        return EXIT_OK
    env.workspace.mkdir(parents=True, exist_ok=True)
    heartbeat = start_heartbeat(ctx, env)
    try:
        return ctx.deps.runner.run_interactive(argv)
    finally:
        if heartbeat is not None:
            heartbeat.stop()


def start_heartbeat(ctx: Ctx, env: LabEnv) -> Heartbeat | None:
    """Start the guard heartbeat thread, or None when the guard is not configured."""
    settings = resolve_settings(ctx, say=False)
    if settings is None:
        if ctx.deps.environ.get("GUARD_BUCKET"):
            ctx.say("Guard heartbeat skipped: check GUARD_BUCKET and LAB_ID.")
        return None
    heartbeat = Heartbeat(lambda: write_heartbeat(ctx, env, settings), ctx.say)
    heartbeat.start()
    return heartbeat


def _terraform_ready(ctx: Ctx, env: LabEnv) -> bool:
    if any(env.terraform_dir.glob("*.tf")):
        return True
    ctx.say(f"TODO: no Terraform files in {env.terraform_dir}. The lab build is not provided yet.")
    return False


def _lifecycle_env(ctx: Ctx) -> LabEnv | None:
    if ctx.in_shell:
        ctx.say("Run this from your own computer, not inside the lab shell.")
        return None
    return engine_or_none(ctx)


def _confirmed(ctx: Ctx, assume_yes: bool, word: str) -> bool:
    if assume_yes:
        return True
    answer = ctx.deps.ask(f"Type '{word}' to continue: ").strip().lower()
    return answer == word


def _write_env_file(ctx: Ctx, env: LabEnv, values: dict[str, str]) -> None:
    text = "".join(f"{k}={v}\n" for k, v in sorted(values.items()))
    write_private(env.env_file, text)
    try:
        os.chmod(env.env_file, 0o600)
    except OSError:
        ctx.say("Note: could not restrict permissions on the lab variables file.")
    ctx.say("Saved lab variables: " + (", ".join(sorted(values)) or "none"))


def _export_outputs(ctx: Ctx, env: LabEnv) -> None:
    result = ctx.deps.runner.run(env.wrap(output_argv(), terraform=True))
    values = outputs_to_env(result.output) if result.returncode == 0 else {}
    if values:
        # Keep credentials from an earlier `lab up`; create random ones for the rest.
        _write_env_file(ctx, env, with_generated({**read_env_file(env.env_file), **values}))
    else:
        ctx.say("No lab variables found in Terraform outputs. 'lab shell' will lack them.")


def _install_inputs(ctx: Ctx, env: LabEnv) -> tuple[dict[str, str], list[str]]:
    """Container-side values for the cluster install, plus a list of problems.

    PULL_SECRET_FILE and SSH_PUBLIC_KEY_FILE must be files under the workspace (the only
    folder mounted); each is translated to its /workspace path. Values are never read here.
    """
    environ = ctx.deps.environ
    values: dict[str, str] = {}
    problems: list[str] = []
    for name in INSTALL_FILE_VARS:
        raw = (environ.get(name) or "").strip()
        if not raw:
            if name == "PULL_SECRET_FILE":
                problems.append("PULL_SECRET_FILE is not set.")
            continue
        translated = workspace_container_path(env.workspace, raw)
        if translated is None:
            problems.append(f"{name} must be a file under the lab workspace ({env.workspace.as_posix()}).")
        elif not Path(raw).expanduser().is_file():
            problems.append(f"{name} does not point to an existing file.")
        else:
            values[name] = translated
    return values, problems


def _install_wrap(env: LabEnv, file_vars: dict[str, str]) -> tuple[str, ...]:
    return env.wrap(install_argv(), terraform=True, extra_pass=INSTALL_PASSTHROUGH, extra_env=file_vars)


def _dry_run_up(ctx: Ctx, env: LabEnv, skip_cluster: bool) -> int:
    for step in (init_argv(), apply_argv(), output_argv()):
        ctx.show(env.wrap(step, terraform=True))
    if skip_cluster:
        ctx.say("  (--skip-cluster: the cluster install step is left out)")
        return EXIT_OK
    file_vars, problems = _install_inputs(ctx, env)
    for problem in problems:
        ctx.say(f"  NOTE: {problem} A real 'lab up' would stop before building anything.")
    ctx.say("  then, once the infrastructure exists, install the cluster (about 45 to 70 minutes, an estimate):")
    shown = {"PULL_SECRET_FILE": "/workspace/<your pull secret file>", **file_vars}
    ctx.show(_install_wrap(env, shown))
    ctx.say("  then install the in-lab services:")
    ctx.show(_platform_wrap(env))
    return EXIT_OK


def cmd_up(ctx: Ctx, args: Namespace) -> int:
    env = _lifecycle_env(ctx)
    if env is None:
        return EXIT_USAGE
    if not _terraform_ready(ctx, env):
        return EXIT_FAIL
    skip_cluster = bool(getattr(args, "skip_cluster", False))
    ctx.say(COST_WARNING)
    if args.dry_run:
        return _dry_run_up(ctx, env, skip_cluster)
    file_vars: dict[str, str] = {}
    if not skip_cluster:
        file_vars, problems = _install_inputs(ctx, env)
        if problems:
            for problem in problems:
                ctx.say(f"ERROR: {problem}")
            ctx.say(PULL_SECRET_HELP.format(workspace=env.workspace.as_posix()))
            ctx.say("Nothing was built.")
            return EXIT_FAIL
    if not _confirmed(ctx, args.yes, CONFIRM_UP):
        ctx.say("Cancelled. Nothing was built.")
        return EXIT_FAIL
    env.state_dir.mkdir(parents=True, exist_ok=True)
    for step in (init_argv(), apply_argv()):
        if ctx.deps.runner.run_interactive(env.wrap(step, terraform=True)) != 0:
            ctx.say("Build failed. Some resources may exist and cost money. Run 'lab down' to clean up.")
            return EXIT_FAIL
    _export_outputs(ctx, env)
    if skip_cluster:
        ctx.say("Infrastructure is up; no cluster was installed (--skip-cluster). Run 'lab up' without it to install.")
        return EXIT_OK
    if ctx.deps.runner.run_interactive(_install_wrap(env, file_vars)) != 0:
        ctx.say(CLUSTER_FAILED)
        return EXIT_FAIL
    ctx.say("Cluster is up. Installing the in-lab services (Gitea, Loki, Grafana, Mattermost and the rest).")
    if ctx.deps.runner.run_interactive(_platform_wrap(env)) != 0:
        ctx.say(PLATFORM_FAILED)
        return EXIT_FAIL
    ctx.say("Lab is up. Remember: run 'lab down' when you finish.")
    return EXIT_OK


PLATFORM_FAILED = (
    "Installing the in-lab services failed. Read the last lines above, fix the cause, and run 'lab platform' again: "
    "it is safe to repeat, and finished services are skipped."
)


def _platform_wrap(env: LabEnv, only: str | None = None) -> tuple[str, ...]:
    return env.wrap(platform_argv(only), platform=True)


def cmd_platform(ctx: Ctx, args: Namespace) -> int:
    """Install Gitea, Loki, Grafana, Mattermost and the other in-lab services on a lab that is already up."""
    env = _lifecycle_env(ctx)
    if env is None:
        return EXIT_USAGE
    only = getattr(args, "only", None)
    if args.dry_run:
        ctx.show(_platform_wrap(env, only))
        return EXIT_OK
    if not (env.state_dir / "kubeconfig").is_file():
        ctx.say("ERROR: no cluster kubeconfig found. Run 'lab up' first.")
        return EXIT_FAIL
    if ctx.deps.runner.run_interactive(_platform_wrap(env, only)) != 0:
        ctx.say(PLATFORM_FAILED)
        return EXIT_FAIL
    ctx.say("In-lab services are installed. Their addresses and sign-ins are saved as lab variables.")
    return EXIT_OK


def cmd_down(ctx: Ctx, args: Namespace) -> int:
    env = _lifecycle_env(ctx)
    if env is None:
        return EXIT_USAGE
    ctx.say(DESTROY_WARNING)
    init = env.wrap(init_argv(), terraform=True)
    cluster = env.wrap(cluster_destroy_argv(), terraform=True)
    argv = env.wrap(destroy_argv(), terraform=True)
    if args.dry_run:
        ctx.say("  first: point Terraform at this lab's saved state (a leftover setting from another lab would find nothing to destroy)")
        ctx.show(init)
        ctx.say("  then: ask the bastion to destroy the cluster and wait for it (up to 60 minutes, an estimate)")
        ctx.show(cluster)
        ctx.say("  then: destroy the AWS infrastructure")
        ctx.show(argv)
        return EXIT_OK
    if not _confirmed(ctx, args.yes, CONFIRM_DOWN):
        ctx.say("Cancelled. Your lab is STILL RUNNING and still costs money.")
        return EXIT_FAIL
    if ctx.deps.runner.run_interactive(init) != 0:
        ctx.say(DOWN_FAILED)
        return EXIT_FAIL
    if ctx.deps.runner.run_interactive(cluster) != 0:
        ctx.say(CLUSTER_DESTROY_FAILED)
        return EXIT_FAIL
    if ctx.deps.runner.run_interactive(argv) != 0:
        ctx.say(DOWN_FAILED)
        return EXIT_FAIL
    for leftover in (env.env_file, env.state_dir / MODULES_FILE, env.state_dir / "kubeconfig"):
        leftover.unlink(missing_ok=True)
    ctx.say("Lab destroyed. Verify in the AWS console that nothing tagged with your lab id remains.")
    return EXIT_OK


def _engine_label(ctx: Ctx) -> str:
    if ctx.in_shell:
        return "inside lab shell"
    try:
        return detect_engine(ctx.deps.which, ctx.deps.environ.get("LAB_ENGINE"))
    except EngineNotFoundError:
        return "none found (install podman or docker)"


def _module_records(ctx: Ctx) -> dict[str, dict[str, str]]:
    path = ctx.workspace / ".lab" / MODULES_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def cmd_status(ctx: Ctx, args: Namespace) -> int:
    ctx.say(f"Container engine: {_engine_label(ctx)}")
    ctx.say(f"Workspace: {ctx.workspace}")
    built = (ctx.workspace / ".lab" / "lab.env").is_file()
    ctx.say("Lab built: " + ("yes (lab variables file present)" if built else "no"))
    ctx.say("Lab variables (values are never shown):")
    for name in CONTRACT_VARS:
        ctx.say(f"  {name}: " + ("set" if ctx.deps.environ.get(name) else "not set"))
    records = _module_records(ctx)
    ctx.say("Modules applied: " + (", ".join(f"{k} ({v.get('action', '?')})" for k, v in records.items()) or "none"))
    active = active_faults(ctx)
    ctx.say("Faults active: " + ("; ".join(f"{m} ({', '.join(ids)})" for m, ids in active.items()) or "none"))
    from labcli.commands_guard import guard_status_lines  # late import: commands_guard imports this module

    for line in guard_status_lines(ctx):
        ctx.say(line)
    return EXIT_OK

"""Argument parsing and dispatch for the lab command."""
from __future__ import annotations

import argparse
import shutil
import sys
from collections.abc import Callable, Sequence
from os import environ as os_environ

from labcli.commands_fault import cmd_break, cmd_restore
from labcli.commands_guard import cmd_keep, cmd_pause, cmd_pull, cmd_resume
from labcli.commands_image import cmd_build_image
from labcli.commands_lab import cmd_down, cmd_platform, cmd_shell, cmd_status, cmd_up
from labcli.commands_module import cmd_modules, cmd_reset, cmd_start
from labcli.context import EXIT_USAGE, Ctx, Deps
from labcli.executor import SubprocessRunner

__all__ = ["Deps", "main", "build_parser", "default_deps"]

Handler = Callable[[Ctx, argparse.Namespace], int]


def _add_dry_run(sub: argparse.ArgumentParser) -> None:
    sub.add_argument("--dry-run", action="store_true", help="print what would run; change nothing")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lab", description="hands-on lab helper")
    cmds = parser.add_subparsers(dest="command")
    _add_dry_run(cmds.add_parser("shell", help="open the lab tools container"))
    for name, text in (("up", "build your lab in AWS (costs money)"), ("down", "destroy your lab (stops the cost)")):
        sub = cmds.add_parser(name, help=text)
        _add_dry_run(sub)
        sub.add_argument("--yes", action="store_true", help="skip the confirmation question")
        if name == "up":
            sub.add_argument("--skip-cluster", action="store_true", help="build the AWS infrastructure only; do not install the cluster")
    for name, text in (("start", "load a module's starting state"), ("reset", "return a module to its starting state")):
        sub = cmds.add_parser(name, help=text)
        sub.add_argument("module")
        _add_dry_run(sub)
    for name, text in (("break", "apply a named fault to practice spotting it"), ("restore", "undo a named fault")):
        sub = cmds.add_parser(name, help=text)
        sub.add_argument("module")
        sub.add_argument("fault", nargs="?", default=None)
        sub.add_argument("--all", action="store_true", help="every fault in the module")
        sub.add_argument("--list", action="store_true", help="show the module's faults and which are active")
        _add_dry_run(sub)
    keep = cmds.add_parser("keep", help="do not pause my lab for idleness for HOURS (default 4, 1 to 24)")
    keep.add_argument("hours", nargs="?", type=int, default=None, metavar="HOURS")
    _add_dry_run(keep)
    for name, text in (("pause", "save and pause my lab now (cheaper, not free)"), ("resume", "resume my paused lab")):
        sub = cmds.add_parser(name, help=text)
        sub.add_argument("--no-wait", action="store_true", help="send the request and return")
        _add_dry_run(sub)
    pull = cmds.add_parser("pull", help="copy the guard's saved lab files to your workspace")
    mode = pull.add_mutually_exclusive_group()
    mode.add_argument("--latest", action="store_true", help="copy the newest save (default)")
    mode.add_argument("--list", action="store_true", help="list available saves")
    _add_dry_run(pull)
    platform = cmds.add_parser("platform", help="install the in-lab services (Gitea, Loki, Grafana, Mattermost, ...); safe to repeat")
    platform.add_argument("--only", metavar="NN", default=None, help="run just the install script that starts with NN (example: 20)")
    _add_dry_run(platform)
    _add_dry_run(cmds.add_parser("build-image", help="build the tools container image locally"))
    cmds.add_parser("status", help="show lab status")
    cmds.add_parser("modules", help="list modules in recommended order")
    return parser


HANDLERS: dict[str, Handler] = {
    "shell": cmd_shell, "up": cmd_up, "platform": cmd_platform, "down": cmd_down, "status": cmd_status,
    "build-image": cmd_build_image, "modules": cmd_modules, "start": cmd_start, "reset": cmd_reset,
    "break": cmd_break, "restore": cmd_restore,
    "keep": cmd_keep, "pause": cmd_pause, "resume": cmd_resume, "pull": cmd_pull,
}


def default_deps() -> Deps:
    return Deps(
        runner=SubprocessRunner(),
        out=sys.stdout,
        ask=input,
        which=shutil.which,
        environ=dict(os_environ),
    )


def main(argv: Sequence[str] | None = None, deps: Deps | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    ctx = Ctx(deps or default_deps())
    if args.command is None:
        ctx.say(parser.format_help())
        return EXIT_USAGE
    try:
        return HANDLERS[args.command](ctx, args)
    except ValueError as err:
        ctx.say(f"ERROR: {err}")
        return EXIT_USAGE

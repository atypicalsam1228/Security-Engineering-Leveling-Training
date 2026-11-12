"""Guard bucket helpers: settings, aws argv builders, local record, heartbeat thread.

The guard (see COST-CONTROLS.md) lives in an S3 bucket. The learner side only
writes small JSON objects and reads the lab's state object. Every aws call runs
in the tools container, so the host needs no aws CLI.
"""
from __future__ import annotations

import json
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from labcli.context import Ctx
from labcli.credentials import read_env_file, write_private
from labcli.environment import CONTAINER_WORKSPACE, LabEnv
from labcli.redact import redact

LAB_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
BUCKET_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
SAVE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
HEARTBEAT_SECONDS = 600.0
DEFAULT_IDLE_HOURS = 2  # guard default; the learner side cannot read the real value
KEEP_DEFAULT_HOURS = 4
KEEP_MAX_HOURS = 24
AWS_TIMEOUT_SECONDS = 120.0
GUARD_FUNCTION = "lab-guard"
LOCAL_RECORD = "guard-local.json"

BILLING_NOTE = "Note: 'lab down' is the way to stop all billing."
NOT_CONFIGURED = (
    "The cost guard is not configured: GUARD_BUCKET is not set. "
    "Run 'lab up' with the guard bucket Terraform variable set, or export GUARD_BUCKET. "
    + BILLING_NOTE
)


@dataclass(frozen=True)
class GuardSettings:
    bucket: str
    lab_id: str


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(text: object) -> datetime | None:
    if not isinstance(text, str):
        return None
    try:
        parsed = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def resolve_settings(ctx: Ctx, say: bool = True) -> GuardSettings | None:
    """GUARD_BUCKET and LAB_ID from the environment, then the saved lab.env. None if unusable."""
    saved = read_env_file(ctx.workspace / ".lab" / "lab.env")
    bucket = ctx.deps.environ.get("GUARD_BUCKET") or saved.get("GUARD_BUCKET", "")
    lab_id = ctx.deps.environ.get("LAB_ID") or saved.get("LAB_ID", "")
    problem = _settings_problem(bucket, lab_id)
    if problem and say:
        ctx.say(problem + " " + BILLING_NOTE)
    return None if problem else GuardSettings(bucket, lab_id)


def _settings_problem(bucket: str, lab_id: str) -> str:
    if not bucket:
        return NOT_CONFIGURED.replace(" " + BILLING_NOTE, "")
    if not lab_id:
        return "LAB_ID is not set. Export your lab id (it is in your lab variables)."
    if not BUCKET_PATTERN.match(bucket):
        return "GUARD_BUCKET does not look like an S3 bucket name."
    if not LAB_ID_PATTERN.match(lab_id):
        return "LAB_ID is not valid (lower-case letters, digits and hyphens only)."
    return ""


def put_argv(bucket: str, key: str, body: str) -> tuple[str, ...]:
    return ("aws", "s3api", "put-object", "--bucket", bucket, "--key", key, "--body", body)


def wake_argv() -> tuple[str, ...]:
    """Run the guard once now, so a pause or resume request is not left waiting for its 15-minute timer."""
    return ("aws", "lambda", "invoke", "--function-name", GUARD_FUNCTION, "--payload", "{}",
            "--cli-binary-format", "raw-in-base64-out", "/tmp/guard-wake.json", "--only-show-errors")


def wake_guard(ctx: Ctx, env: LabEnv) -> bool:
    """Best effort: True if the guard was woken. Learner accounts may not be allowed to; then the timer applies."""
    try:
        result = ctx.deps.runner.run(env.wrap(wake_argv()), AWS_TIMEOUT_SECONDS)
    except OSError:
        return False
    return result.returncode == 0


def get_argv(bucket: str, key: str) -> tuple[str, ...]:
    return ("aws", "s3", "cp", f"s3://{bucket}/{key}", "-", "--only-show-errors")


def body_path(env: LabEnv, name: str) -> tuple[Path, str]:
    """(host path, path as the aws command sees it) of a workspace file."""
    host = env.state_dir / name
    seen = host.as_posix() if env.in_shell else f"{CONTAINER_WORKSPACE}/.lab/{name}"
    return host, seen


def put_json(ctx: Ctx, env: LabEnv, bucket: str, key: str, payload: dict[str, str]) -> str:
    """Upload a small JSON object. Returns "" on success, else redacted error text."""
    name = "guard-" + key.replace("/", "-")
    host, seen = body_path(env, name)
    try:
        write_private(host, json.dumps(payload) + "\n")
        result = ctx.deps.runner.run(env.wrap(put_argv(bucket, key, seen)), AWS_TIMEOUT_SECONDS)
    except OSError as err:
        return redact(str(err), ctx.secrets())
    return "" if result.returncode == 0 else redact(result.output.strip() or "aws failed", ctx.secrets())


def get_json(ctx: Ctx, env: LabEnv, bucket: str, key: str) -> dict | None:
    """Read a JSON object, or None if it is missing, unreadable or not an object."""
    try:
        result = ctx.deps.runner.run(env.wrap(get_argv(bucket, key)), AWS_TIMEOUT_SECONDS)
    except OSError:
        return None
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.output)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def read_local(env: LabEnv) -> dict[str, str]:
    try:
        data = json.loads((env.state_dir / LOCAL_RECORD).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {k: v for k, v in data.items() if isinstance(v, str)} if isinstance(data, dict) else {}


def update_local(env: LabEnv, **fields: str) -> None:
    """Remember our own last heartbeat / keep time (the learner cannot read them back from S3)."""
    try:
        write_private(env.state_dir / LOCAL_RECORD, json.dumps({**read_local(env), **fields}) + "\n")
    except OSError:
        pass  # only affects the status line


def write_heartbeat(ctx: Ctx, env: LabEnv, settings: GuardSettings) -> str:
    now = ctx.deps.now()
    error = put_json(ctx, env, settings.bucket, f"heartbeat/{settings.lab_id}", {"ts": iso(now)})
    if not error:
        update_local(env, heartbeat=iso(now))
    return error


def pause_estimate(local: dict[str, str], now: datetime) -> timedelta | None:
    """Time left before an idle pause, assuming DEFAULT_IDLE_HOURS. None if unknown."""
    times = []
    beat = parse_iso(local.get("heartbeat"))
    if beat:
        times.append(beat + timedelta(hours=DEFAULT_IDLE_HOURS))
    keep = parse_iso(local.get("keep_until"))
    if keep:
        times.append(keep)
    return max(times) - now if times else None


class Heartbeat:
    """Calls beat() now and every interval until stop(). Never raises; reports a failure once."""

    def __init__(
        self,
        beat: Callable[[], str],
        report: Callable[[str], None],
        interval: float = HEARTBEAT_SECONDS,
        wait: Callable[[float], bool] | None = None,
    ) -> None:
        self._beat = beat
        self._report = report
        self._interval = interval
        self._stop = threading.Event()
        self._wait = wait or self._stop.wait
        self._reported = False
        self._thread = threading.Thread(target=self.run, name="lab-heartbeat", daemon=True)

    def _once(self) -> None:
        try:
            error = self._beat()
        except Exception as err:  # a heartbeat must never break the shell
            error = str(err) or type(err).__name__
        if error and not self._reported:
            self._reported = True
            self._report(
                "Heartbeat failed (the shell keeps working): " + error
                + "\nThe guard may pause your lab as idle. " + BILLING_NOTE
            )

    def run(self) -> None:
        self._once()
        while not self._wait(self._interval):
            self._once()

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=AWS_TIMEOUT_SECONDS + 5)

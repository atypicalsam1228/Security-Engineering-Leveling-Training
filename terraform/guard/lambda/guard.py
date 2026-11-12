"""Lab guard: idle pause, spend limit and deadline destroy (see COST-CONTROLS.md).

decide() is a pure function (no AWS calls). Guard applies its decisions with
boto3 clients that are passed in, so tests can use fakes. dry_run=true means:
compute and email the action, change nothing, record last_run only.

Nothing here has run on AWS.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import re
from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Optional

LOG = logging.getLogger("lab-guard")
LOG.setLevel(logging.INFO)

UTC = dt.timezone.utc
EPOCH = dt.datetime(1970, 1, 1, tzinfo=UTC)

LAB_ID_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,40}")
BUDGET_NAME_RE = re.compile(r"([a-z0-9][a-z0-9-]{0,40})-monthly")
BUCKET_RE = re.compile(r"[a-z0-9][a-z0-9.-]{2,62}")
DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")

STATUSES = frozenset(
    {"running", "warned", "saving", "pausing", "paused", "resuming", "destroying", "destroyed", "error"}
)
IN_PROGRESS = frozenset({"saving", "pausing", "resuming", "destroying"})
ACTION_KINDS = frozenset({"none", "warn", "save_and_pause", "resume", "destroy"})
STUCK_AFTER = dt.timedelta(hours=2)
MAX_KEEP = dt.timedelta(hours=24)
NOTICE_REPEAT = dt.timedelta(hours=6)
BASTION_ROLE_TAG = "openshift-install-fips"
EXPORT_COMMAND = "/opt/lab/export.sh"
SSM_FAILED = frozenset({"Failed", "Cancelled", "Cancelling", "TimedOut"})
BUILD_FAILED = frozenset({"FAILED", "FAULT", "STOPPED", "TIMED_OUT"})
BUILD_ACTION = {"saving": "pause", "pausing": "pause", "resuming": "resume", "destroying": "destroy"}
BUILD_STATUS = {"pause": "pausing", "resume": "resuming", "destroy": "destroying"}


# ---------------------------------------------------------------- parsing

def parse_ts(value: Any, name: str) -> dt.datetime:
    """Parse an ISO 8601 timestamp into an aware UTC datetime; ValueError otherwise."""
    if not isinstance(value, str):
        raise ValueError(f"{name}: expected an ISO 8601 string")
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{name}: not ISO 8601: {value[:40]!r}") from None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def iso(value: Optional[dt.datetime]) -> Optional[str]:
    return None if value is None else value.astimezone(UTC).isoformat()


def valid_lab_id(value: Any) -> bool:
    return isinstance(value, str) and LAB_ID_RE.fullmatch(value) is not None


def _require_dict(doc: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(doc, dict):
        raise ValueError(f"{name}: expected a JSON object")
    return doc


def _opt_str(doc: Mapping[str, Any], key: str, name: str) -> Optional[str]:
    value = doc.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name}.{key}: expected a string")
    return value


# ---------------------------------------------------------------- data

@dataclass(frozen=True)
class Config:
    idle_hours: int = 2
    warn_minutes: int = 30
    build_grace_hours: int = 2
    pause_destroy_days: int = 7
    dry_run: bool = True

    def __post_init__(self) -> None:
        if self.idle_hours < 1:
            raise ValueError("idle_hours must be >= 1")
        if not 0 <= self.warn_minutes < self.idle_hours * 60:
            raise ValueError("warn_minutes must be >= 0 and < idle_hours * 60")
        if self.build_grace_hours < 0:
            raise ValueError("build_grace_hours must be >= 0")
        if self.pause_destroy_days < 1:
            raise ValueError("pause_destroy_days must be >= 1")


@dataclass(frozen=True)
class Registration:
    lab_id: str
    region: str
    state_bucket: str
    state_key: str
    state_kms_key_arn: str
    destroy_after: dt.date
    alert_email: str
    registered_at: dt.datetime
    tf_vars: Mapping[str, Any]

    @classmethod
    def from_json(cls, doc: Any, lab_id: str) -> "Registration":
        d = _require_dict(doc, "registration")
        for key in ("region", "state_bucket", "state_key", "state_kms_key_arn", "destroy_after", "alert_email"):
            if not isinstance(d.get(key), str) or not d[key]:
                raise ValueError(f"registration.{key}: missing or not a string")
        if d.get("lab_id") != lab_id:
            raise ValueError("registration.lab_id does not match its key")
        if not DATE_RE.fullmatch(d["destroy_after"]):
            raise ValueError("registration.destroy_after: expected YYYY-MM-DD")
        try:
            destroy_after = dt.date.fromisoformat(d["destroy_after"])
        except ValueError:
            raise ValueError("registration.destroy_after: not a valid date") from None
        tf_vars = d.get("tf_vars", {})
        if not isinstance(tf_vars, dict):
            raise ValueError("registration.tf_vars: expected an object")
        return cls(
            lab_id=lab_id, region=d["region"], state_bucket=d["state_bucket"], state_key=d["state_key"],
            state_kms_key_arn=d["state_kms_key_arn"], destroy_after=destroy_after,
            alert_email=d["alert_email"], registered_at=parse_ts(d.get("registered_at"), "registration.registered_at"),
            tf_vars=tf_vars,
        )


@dataclass(frozen=True)
class LabState:
    status: str = "running"
    since: Optional[dt.datetime] = None
    paused_at: Optional[dt.datetime] = None
    last_notice: Optional[Mapping[str, str]] = None  # {"kind": ..., "ts": ...}
    last_error: Optional[str] = None
    last_run: Optional[dt.datetime] = None
    # Extensions to the contract, used for polling and idle accounting.
    resumed_at: Optional[dt.datetime] = None
    command_id: Optional[str] = None
    instance_id: Optional[str] = None
    build_id: Optional[str] = None
    then: Optional[str] = None  # "pause" or "destroy": what follows a successful save

    @classmethod
    def initial(cls, registration: Registration) -> "LabState":
        return cls(status="running", since=registration.registered_at)

    @classmethod
    def from_json(cls, doc: Any) -> "LabState":
        d = _require_dict(doc, "state")
        status = d.get("status")
        if status not in STATUSES:
            raise ValueError(f"state.status: invalid {str(status)[:30]!r}")

        def ts(key: str) -> Optional[dt.datetime]:
            return None if d.get(key) is None else parse_ts(d[key], f"state.{key}")

        notice = d.get("last_notice")
        if notice is not None:
            if not isinstance(notice, dict) or notice.get("kind") is None or notice.get("ts") is None:
                raise ValueError("state.last_notice: expected {kind, ts}")
            notice = {"kind": str(notice["kind"]), "ts": str(notice["ts"])}
        then = _opt_str(d, "then", "state")
        if then not in (None, "pause", "destroy"):
            raise ValueError("state.then: invalid")
        return cls(
            status=status, since=ts("since"), paused_at=ts("paused_at"), last_notice=notice,
            last_error=_opt_str(d, "last_error", "state"), last_run=ts("last_run"), resumed_at=ts("resumed_at"),
            command_id=_opt_str(d, "command_id", "state"), instance_id=_opt_str(d, "instance_id", "state"),
            build_id=_opt_str(d, "build_id", "state"), then=then,
        )

    def to_json(self) -> dict:
        return {
            "status": self.status, "since": iso(self.since), "paused_at": iso(self.paused_at),
            "last_notice": dict(self.last_notice) if self.last_notice else None,
            "last_error": self.last_error, "last_run": iso(self.last_run), "resumed_at": iso(self.resumed_at),
            "command_id": self.command_id, "instance_id": self.instance_id, "build_id": self.build_id,
            "then": self.then,
        }


@dataclass(frozen=True)
class Action:
    kind: str
    reason: str
    dry_run: bool = False
    clear_warning: bool = False      # none: activity resumed, reset warned -> running
    consumes_request: bool = False   # the request caused this action or is moot; delete it

    def __post_init__(self) -> None:
        if self.kind not in ACTION_KINDS:
            raise ValueError(f"invalid action kind {self.kind!r}")


def effective_state(registration: Registration, state: Optional[LabState]) -> LabState:
    """Missing state is a fresh running lab; a destroyed lab re-registered later is fresh too."""
    if state is None:
        return LabState.initial(registration)
    if state.status == "destroyed" and registration.registered_at > (state.since or EPOCH):
        return LabState.initial(registration)
    return state


# ---------------------------------------------------------------- decide

def _act(config: Config, kind: str, reason: str, **kw: bool) -> Action:
    return Action(kind, reason, dry_run=config.dry_run, **kw)


def decide(
    now: dt.datetime,
    registration: Optional[Registration],
    heartbeat: Optional[dt.datetime],
    keep: Optional[dt.datetime],
    state: Optional[LabState],
    request: Optional[str],
    config: Config,
) -> Action:
    """Pure decision for one lab. keep is the `until` time; request is "pause", "resume" or None."""
    if registration is None:
        return Action("none", "no registration")
    st = effective_state(registration, state)
    if st.status == "destroyed":
        return Action("none", "already destroyed")
    if st.status == "error":
        return Action("none", "lab is in error; an operator must clear state")
    if st.status in IN_PROGRESS:
        return Action("none", f"{st.status} in progress")
    if now.date() > registration.destroy_after:
        return _act(config, "destroy", f"destroy_after {registration.destroy_after} has passed")
    if st.status == "paused":
        return _decide_paused(now, st, request, config)
    return _decide_running(now, registration, st, heartbeat, keep, request, config)


def _decide_paused(now: dt.datetime, st: LabState, request: Optional[str], config: Config) -> Action:
    paused_at = st.paused_at or st.since or now
    if now - paused_at >= dt.timedelta(days=config.pause_destroy_days):
        return _act(config, "destroy", f"paused for {config.pause_destroy_days} days or more")
    if request == "resume":
        return _act(config, "resume", "resume requested", consumes_request=True)
    if request == "pause":
        return Action("none", "pause requested but lab is already paused", consumes_request=True)
    return Action("none", "paused")


def _decide_running(
    now: dt.datetime, reg: Registration, st: LabState, heartbeat: Optional[dt.datetime],
    keep: Optional[dt.datetime], request: Optional[str], config: Config,
) -> Action:
    if request == "pause":
        return _act(config, "save_and_pause", "pause requested", consumes_request=True)
    if request == "resume":
        return Action("none", "resume requested but lab is not paused", consumes_request=True)
    grace_end = reg.registered_at + dt.timedelta(hours=config.build_grace_hours)
    if now < grace_end:
        return Action("none", "within build grace period")
    if keep is not None:
        keep = min(keep, now + MAX_KEEP)
        if keep > now:
            return Action("none", "keep active", clear_warning=st.status == "warned")
    marks = [reg.registered_at, st.resumed_at, heartbeat, keep]
    last_activity = min(max(m for m in marks if m is not None), now)
    idle = now - last_activity
    idle_limit = dt.timedelta(hours=config.idle_hours)
    warn_at = idle_limit - dt.timedelta(minutes=config.warn_minutes)
    if idle >= idle_limit:
        return _act(config, "save_and_pause", f"idle {_fmt(idle)}, limit {config.idle_hours}h")
    if idle >= warn_at and st.status != "warned":
        return _act(config, "warn", f"idle {_fmt(idle)}, pausing at {config.idle_hours}h")
    if idle < warn_at and st.status == "warned":
        return Action("none", "activity seen", clear_warning=True)
    return Action("none", "active" if idle < warn_at else "warned, waiting")


def _fmt(delta: dt.timedelta) -> str:
    return f"{int(delta.total_seconds() // 60)}min"


# ---------------------------------------------------------------- spend

def lab_from_budget_message(message: Any) -> Optional[str]:
    """Extract the lab id from an AWS Budgets SNS message (format unverified)."""
    if not isinstance(message, str):
        return None
    found = re.search(r"Budget Name:\s*(\S+)", message)
    if not found:
        return None
    match = BUDGET_NAME_RE.fullmatch(found.group(1))
    return match.group(1) if match else None


# ---------------------------------------------------------------- handlers

def _error_code(exc: BaseException) -> str:
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        return str(response.get("Error", {}).get("Code", ""))
    return type(exc).__name__


def _is_not_found(exc: BaseException) -> bool:
    return _error_code(exc) in {"NoSuchKey", "404", "NotFound"}


@dataclass
class Guard:
    s3: Any
    ssm: Any
    ec2: Any
    codebuild: Any
    sns: Any
    bucket: str
    notify_topic: str
    budget_topic: str
    project: str
    config: Config
    region: str = ""
    sent: list = field(default_factory=list)

    # -- io
    def _read(self, key: str) -> Optional[Any]:
        try:
            body = self.s3.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except Exception as exc:  # noqa: BLE001 - not-found is expected, everything else re-raised
            if _is_not_found(exc):
                return None
            raise
        try:
            return json.loads(body)
        except ValueError:
            raise ValueError(f"{key}: not valid JSON") from None

    def _write_state(self, lab_id: str, state: LabState, now: dt.datetime) -> None:
        body = json.dumps(replace(state, last_run=now).to_json()).encode()
        self.s3.put_object(Bucket=self.bucket, Key=f"state/{lab_id}.json", Body=body, ContentType="application/json")

    def _delete(self, key: str) -> None:
        self.s3.delete_object(Bucket=self.bucket, Key=key)

    def notify(self, subject: str, message: str) -> None:
        self.sns.publish(TopicArn=self.notify_topic, Subject=subject[:99], Message=message)

    # -- loading
    def _load_state(self, lab_id: str) -> Optional[LabState]:
        doc = self._read(f"state/{lab_id}.json")
        return None if doc is None else LabState.from_json(doc)

    def _load_registration(self, lab_id: str) -> Optional[Registration]:
        doc = self._read(f"labs/{lab_id}/registration.json")
        if doc is None:
            return None
        reg = Registration.from_json(doc, lab_id)
        if self.region and reg.region != self.region:
            raise ValueError(f"registration region {reg.region} differs from guard region {self.region}")
        return reg

    def _load_inputs(self, lab_id: str) -> tuple:
        hb_doc = self._read(f"heartbeat/{lab_id}")
        heartbeat = None
        if hb_doc is not None:
            heartbeat = parse_ts(_require_dict(hb_doc, "heartbeat").get("ts"), "heartbeat.ts")
        keep_doc = self._read(f"keep/{lab_id}")
        keep = None
        if keep_doc is not None:
            keep = parse_ts(_require_dict(keep_doc, "keep").get("until"), "keep.until")
        req_doc = self._read(f"requests/{lab_id}.json")
        request = None
        if req_doc is not None:
            request = _require_dict(req_doc, "request").get("action")
            if request not in ("pause", "resume"):
                self._delete(f"requests/{lab_id}.json")
                raise ValueError("request.action must be pause or resume (request deleted)")
        return heartbeat, keep, request

    # -- one lab
    def run_lab(self, lab_id: str, now: dt.datetime) -> str:
        """Process one lab. Never raises: failures are recorded in state and emailed."""
        if not valid_lab_id(lab_id):
            LOG.warning("skipping invalid lab id %r", str(lab_id)[:50])
            return "skipped: invalid lab id"
        state: Optional[LabState] = None
        try:
            state = self._load_state(lab_id)
            reg = self._load_registration(lab_id)
            if state is not None and state.status in IN_PROGRESS:
                return self._poll(lab_id, state, now)
            if reg is None:
                return "skipped: no registration"
            heartbeat, keep, request = self._load_inputs(lab_id)
            action = decide(now, reg, heartbeat, keep, state, request, self.config)
            return self._apply(lab_id, reg, effective_state(reg, state), action, now)
        except Exception as exc:  # noqa: BLE001 - recorded and emailed below
            return self._record_failure(lab_id, state, exc, now)

    def _record_failure(self, lab_id: str, state: Optional[LabState], exc: BaseException, now: dt.datetime) -> str:
        message = f"{type(exc).__name__}: {exc}"[:500]
        LOG.exception("lab %s failed", lab_id)
        try:
            if state is not None:
                if state.last_error == message:
                    return f"error (already reported): {message}"
                self._write_state(lab_id, replace(state, last_error=message), now)
            self.notify(f"[lab-guard] {lab_id}: error", f"Lab {lab_id}: {message}")
        except Exception:  # noqa: BLE001 - last resort, logged
            LOG.exception("could not record failure for %s", lab_id)
        return f"error: {message}"

    def _set_error(self, lab_id: str, state: LabState, message: str, now: dt.datetime) -> str:
        self._write_state(lab_id, replace(state, status="error", since=now, last_error=message[:500]), now)
        self.notify(f"[lab-guard] {lab_id}: error", f"Lab {lab_id} is now in error: {message}\n"
                    "The guard will not act on it until an operator fixes the cause and clears state/"
                    f"{lab_id}.json.")
        return f"error: {message}"

    # -- applying a decision
    def _apply(self, lab_id: str, reg: Registration, st: LabState, action: Action, now: dt.datetime) -> str:
        if action.kind == "none":
            return self._apply_none(lab_id, st, action, now)
        if action.dry_run:
            return self._dry_notice(lab_id, st, action, now)
        if action.kind == "warn":
            self.notify(f"[lab-guard] {lab_id}: pausing soon",
                        f"Lab {lab_id} has been idle ({action.reason}). It will be saved and paused soon. "
                        "Run `lab keep` to extend.")
            self._write_state(lab_id, replace(st, status="warned", since=now, last_error=None,
                                              last_notice={"kind": "warn", "ts": iso(now)}), now)
        elif action.kind == "resume":
            self._start_build(lab_id, st, "resume", now)
        else:
            self._begin_save(lab_id, st, "destroy" if action.kind == "destroy" else "pause", now)
        if action.consumes_request:
            self._delete(f"requests/{lab_id}.json")
        return f"{action.kind}: {action.reason}"

    def _apply_none(self, lab_id: str, st: LabState, action: Action, now: dt.datetime) -> str:
        if self.config.dry_run:
            self._write_state(lab_id, st, now)
            return f"none (dry run): {action.reason}"
        if action.clear_warning:
            self._write_state(lab_id, replace(st, status="running", since=now), now)
        if action.consumes_request:
            self._delete(f"requests/{lab_id}.json")
        return f"none: {action.reason}"

    def _dry_notice(self, lab_id: str, st: LabState, action: Action, now: dt.datetime) -> str:
        notice = st.last_notice
        recent = bool(notice) and notice.get("kind") == f"dry:{action.kind}" and \
            now - parse_ts(notice["ts"], "last_notice.ts") < NOTICE_REPEAT
        if not recent:
            self.notify(f"[lab-guard] DRY RUN {lab_id}: would {action.kind}",
                        f"dry_run is on. Lab {lab_id}: would {action.kind} ({action.reason}). Nothing was changed.")
            st = replace(st, last_notice={"kind": f"dry:{action.kind}", "ts": iso(now)})
        self._write_state(lab_id, st, now)
        return f"dry run, would {action.kind}: {action.reason}"

    def _bastion_ids(self, lab_id: str) -> list:
        resp = self.ec2.describe_instances(Filters=[
            {"Name": "tag:LabId", "Values": [lab_id]},
            {"Name": "tag:Role", "Values": [BASTION_ROLE_TAG]},
            {"Name": "instance-state-name", "Values": ["running"]},
        ])
        return [i["InstanceId"] for r in resp.get("Reservations", []) for i in r.get("Instances", [])]

    def _begin_save(self, lab_id: str, st: LabState, then: str, now: dt.datetime) -> None:
        if st.status == "paused":  # saved when it paused; the bastion is gone
            self._start_build(lab_id, st, then, now)
            return
        ids = self._bastion_ids(lab_id)
        if not ids:
            raise RuntimeError(f"no running bastion tagged LabId={lab_id} to save through; "
                               f"not doing {then} without a save")
        if not BUCKET_RE.fullmatch(self.bucket):
            raise RuntimeError("guard bucket name is invalid")
        out = self.ssm.send_command(
            InstanceIds=[ids[0]], DocumentName="AWS-RunShellScript", TimeoutSeconds=1800,
            Comment=f"lab-guard save {lab_id}"[:100],
            Parameters={"commands": [f"{EXPORT_COMMAND} {lab_id} {self.bucket}"]},
        )
        self._write_state(lab_id, replace(st, status="saving", since=now, last_error=None, then=then,
                                          command_id=out["Command"]["CommandId"], instance_id=ids[0],
                                          build_id=None), now)

    def _start_build(self, lab_id: str, st: LabState, action: str, now: dt.datetime) -> None:
        out = self.codebuild.start_build(
            projectName=self.project,
            environmentVariablesOverride=[
                {"name": "ACTION", "value": action, "type": "PLAINTEXT"},
                {"name": "LAB_ID", "value": lab_id, "type": "PLAINTEXT"},
            ],
            idempotencyToken=f"{lab_id}-{action}-{now:%Y%m%d%H}"[:120],
        )
        self._write_state(lab_id, replace(st, status=BUILD_STATUS[action], since=now, last_error=None,
                                          build_id=out["build"]["id"], command_id=None, instance_id=None), now)

    # -- polling in-progress work
    def _poll(self, lab_id: str, st: LabState, now: dt.datetime) -> str:
        if now - (st.since or now) > STUCK_AFTER:
            return self._set_error(lab_id, st, f"stuck in {st.status} for more than 2 hours", now)
        if st.status == "saving":
            return self._poll_save(lab_id, st, now)
        return self._poll_build(lab_id, st, now)

    def _poll_save(self, lab_id: str, st: LabState, now: dt.datetime) -> str:
        try:
            inv = self.ssm.get_command_invocation(CommandId=st.command_id, InstanceId=st.instance_id)
        except Exception as exc:  # noqa: BLE001
            if _error_code(exc) == "InvocationDoesNotExist":
                return "saving: invocation not visible yet"
            raise
        status = inv.get("Status", "")
        if status in SSM_FAILED:
            return self._set_error(lab_id, st, f"save command {status}; nothing paused or destroyed", now)
        if status != "Success":
            return f"saving: {status}"
        if self.config.dry_run:
            return "saving finished; dry_run is on, not starting the build"
        self._start_build(lab_id, st, st.then or "pause", now)
        return f"save done, started {st.then or 'pause'} build"

    def _poll_build(self, lab_id: str, st: LabState, now: dt.datetime) -> str:
        out = self.codebuild.batch_get_builds(ids=[st.build_id])
        builds = out.get("builds", [])
        if not builds:
            return self._set_error(lab_id, st, f"build {st.build_id} not found", now)
        status = builds[0].get("buildStatus", "")
        if status in BUILD_FAILED:
            return self._set_error(lab_id, st, f"build {st.build_id} {status} (see its CodeBuild log)", now)
        if status != "SUCCEEDED":
            return f"{st.status}: build {status}"
        done = {"pausing": replace(st, status="paused", paused_at=now),
                "resuming": replace(st, status="running", resumed_at=now),
                "destroying": replace(st, status="destroyed")}[st.status]
        final = replace(done, since=now, last_error=None, build_id=None, then=None)
        self._write_state(lab_id, final, now)
        self.notify(f"[lab-guard] {lab_id}: {final.status}", f"Lab {lab_id} is now {final.status}.")
        return final.status

    # -- all labs
    def _lab_ids(self) -> list:
        found = set()
        for prefix, delim in (("labs/", "/"), ("state/", None)):
            token = None
            while True:
                kw = {"Bucket": self.bucket, "Prefix": prefix}
                if delim:
                    kw["Delimiter"] = delim
                if token:
                    kw["ContinuationToken"] = token
                resp = self.s3.list_objects_v2(**kw)
                for item in resp.get("CommonPrefixes", []):
                    found.add(item["Prefix"][len(prefix):].rstrip("/"))
                for item in resp.get("Contents", []):
                    name = item["Key"][len(prefix):]
                    if name.endswith(".json"):
                        found.add(name[:-5])
                if not resp.get("IsTruncated"):
                    break
                token = resp.get("NextContinuationToken")
        return sorted(found)

    def run_all(self, now: dt.datetime) -> dict:
        return {lab: self.run_lab(lab, now) for lab in self._lab_ids()}

    # -- spend limit
    def run_budget(self, event: Mapping[str, Any], now: dt.datetime) -> dict:
        results = {}
        for record in event.get("Records", []):
            sns = record.get("Sns", {})
            if sns.get("TopicArn") != self.budget_topic:
                LOG.warning("ignoring SNS record from unexpected topic")
                continue
            lab_id = lab_from_budget_message(sns.get("Message"))
            if lab_id is None:
                self.notify("[lab-guard] unrecognised budget notification",
                            "A message on the budget topic did not name a <lab_id>-monthly budget; ignored.")
                continue
            results[lab_id] = self._spend_destroy(lab_id, now)
        return results

    def _spend_destroy(self, lab_id: str, now: dt.datetime) -> str:
        state: Optional[LabState] = None
        try:
            state = self._load_state(lab_id)
            reg = self._load_registration(lab_id)
            if reg is None:
                return "skipped: no registration"
            st = effective_state(reg, state)
            if st.status in IN_PROGRESS or st.status in ("destroyed", "error"):
                return f"skipped: lab is {st.status}"
            action = _act(self.config, "destroy", "spend limit reached")
            return self._apply(lab_id, reg, st, action, now)
        except Exception as exc:  # noqa: BLE001
            return self._record_failure(lab_id, state, exc, now)


# ---------------------------------------------------------------- lambda entry

def _env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"missing environment variable {name}")
    return value


def config_from_env(env: Mapping[str, str]) -> Config:
    return Config(
        idle_hours=int(env.get("IDLE_HOURS", "2")), warn_minutes=int(env.get("WARN_MINUTES", "30")),
        build_grace_hours=int(env.get("BUILD_GRACE_HOURS", "2")),
        pause_destroy_days=int(env.get("PAUSE_DESTROY_DAYS", "7")),
        dry_run=env.get("DRY_RUN", "true").strip().lower() != "false",  # anything but "false" is dry
    )


def make_guard() -> Guard:
    import boto3  # imported here so unit tests need no AWS SDK

    return Guard(
        s3=boto3.client("s3"), ssm=boto3.client("ssm"), ec2=boto3.client("ec2"),
        codebuild=boto3.client("codebuild"), sns=boto3.client("sns"), bucket=_env("GUARD_BUCKET"),
        notify_topic=_env("NOTIFY_TOPIC_ARN"), budget_topic=_env("BUDGET_TOPIC_ARN"),
        project=_env("CODEBUILD_PROJECT"), config=config_from_env(os.environ),
        region=os.environ.get("GUARD_REGION", ""),
    )


def handler(event: Any, context: Any) -> dict:
    guard = make_guard()
    now = dt.datetime.now(UTC)
    if isinstance(event, dict) and event.get("Records"):
        result = guard.run_budget(event, now)
    else:
        result = guard.run_all(now)
    LOG.info(json.dumps({"dry_run": guard.config.dry_run, "result": result}))
    return {"dry_run": guard.config.dry_run, "result": result}

"""Unit tests for guard.py. Fake AWS clients, no network."""

import datetime as dt
import io
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lambda"))

import guard  # noqa: E402
from guard import Action, Config, Guard, LabState, Registration, decide  # noqa: E402

UTC = dt.timezone.utc
T0 = dt.datetime(2030, 1, 10, 12, 0, tzinfo=UTC)
LAB = "lab-one"
BUCKET = "guard-bucket-test"
TOPIC = "arn:aws:sns:us-east-1:111111111111:lab-guard-notify"
BUDGET = "arn:aws:sns:us-east-1:111111111111:lab-guard-budget"
CFG = Config(idle_hours=2, warn_minutes=30, build_grace_hours=2, pause_destroy_days=7, dry_run=False)
DRY = Config(dry_run=True)


def reg_doc(**over):
    doc = {
        "lab_id": LAB, "region": "us-east-1", "state_bucket": "sb", "state_key": "lab/terraform.tfstate",
        "state_kms_key_arn": "arn:aws:kms:us-east-1:111111111111:key/x", "destroy_after": "2030-02-01",
        "alert_email": "a@example.invalid", "registered_at": (T0 - dt.timedelta(hours=10)).isoformat(),
        "tf_vars": {},
    }
    doc.update(over)
    return doc


def reg(**over):
    return Registration.from_json(reg_doc(**over), LAB)


def mins(n):
    return T0 - dt.timedelta(minutes=n)


# ------------------------------------------------------------ decide: pure

def test_no_registration_does_nothing():
    assert decide(T0, None, mins(1), None, None, "pause", CFG).kind == "none"


def test_active_lab_no_action():
    a = decide(T0, reg(), mins(10), None, None, None, CFG)
    assert a.kind == "none"


def test_tier1_warn_at_idle_minus_warn_minutes():
    a = decide(T0, reg(), mins(90), None, None, None, CFG)
    assert a.kind == "warn"
    assert decide(T0, reg(), mins(89), None, None, None, CFG).kind == "none"


def test_warn_not_repeated_when_already_warned():
    st = LabState(status="warned", since=mins(10))
    assert decide(T0, reg(), mins(100), None, st, None, CFG).kind == "none"


def test_warned_then_activity_clears_warning():
    st = LabState(status="warned", since=mins(10))
    a = decide(T0, reg(), mins(5), None, st, None, CFG)
    assert a.kind == "none" and a.clear_warning


def test_tier2_pause_at_idle_hours():
    a = decide(T0, reg(), mins(120), None, None, None, CFG)
    assert a.kind == "save_and_pause"
    st = LabState(status="warned", since=mins(10))
    assert decide(T0, reg(), mins(150), None, st, None, CFG).kind == "save_and_pause"


def test_tier3_destroy_after_pause_days():
    st = LabState(status="paused", since=T0 - dt.timedelta(days=7), paused_at=T0 - dt.timedelta(days=7))
    assert decide(T0, reg(), None, None, st, None, CFG).kind == "destroy"
    st2 = LabState(status="paused", paused_at=T0 - dt.timedelta(days=6, hours=23))
    assert decide(T0, reg(), None, None, st2, None, CFG).kind == "none"


def test_tier3_destroy_after_date_passed():
    r = reg(destroy_after="2030-01-09")
    assert decide(T0, r, mins(1), None, None, None, CFG).kind == "destroy"
    r_today = reg(destroy_after="2030-01-10")
    assert decide(T0, r_today, mins(1), None, None, None, CFG).kind == "none"


def test_destroy_after_applies_to_paused_lab():
    st = LabState(status="paused", paused_at=mins(5))
    assert decide(T0, reg(destroy_after="2030-01-01"), None, None, st, None, CFG).kind == "destroy"


def test_keep_blocks_pause_and_expired_keep_counts_as_activity():
    future = T0 + dt.timedelta(hours=1)
    assert decide(T0, reg(), mins(500), future, None, None, CFG).kind == "none"
    just_expired = T0 - dt.timedelta(minutes=10)
    assert decide(T0, reg(), mins(500), just_expired, None, None, CFG).kind == "none"
    long_expired = T0 - dt.timedelta(hours=3)
    assert decide(T0, reg(), mins(500), long_expired, None, None, CFG).kind == "save_and_pause"


def test_keep_is_clamped_to_24_hours():
    far = T0 + dt.timedelta(days=30)
    a = decide(T0, reg(), None, far, None, None, CFG)
    assert a.kind == "none"  # still honoured, but only as far as 24h in the future


def test_build_grace_blocks_pause():
    r = reg(registered_at=(T0 - dt.timedelta(minutes=90)).isoformat())
    assert decide(T0, r, None, None, None, None, CFG).kind == "none"
    r2 = reg(registered_at=(T0 - dt.timedelta(minutes=121)).isoformat())
    assert decide(T0, r2, None, None, None, None, CFG).kind == "save_and_pause"


def test_missing_heartbeat_counts_from_registration():
    r = reg(registered_at=(T0 - dt.timedelta(hours=3)).isoformat())
    assert decide(T0, r, None, None, None, None, CFG).kind == "save_and_pause"
    r2 = reg(registered_at=(T0 - dt.timedelta(minutes=125)).isoformat())
    assert decide(T0, r2, None, None, None, None, Config(build_grace_hours=0, dry_run=False)).kind == "save_and_pause"


def test_future_heartbeat_is_capped_to_now():
    a = decide(T0, reg(), T0 + dt.timedelta(days=5), None, None, None, CFG)
    assert a.kind == "none"


def test_resume_counts_as_activity():
    st = LabState(status="running", resumed_at=mins(10))
    assert decide(T0, reg(), mins(600), None, st, None, CFG).kind == "none"


def test_request_pause_overrides_activity_and_grace():
    r = reg(registered_at=mins(5).isoformat())
    a = decide(T0, r, mins(1), None, None, "pause", CFG)
    assert a.kind == "save_and_pause" and a.consumes_request


def test_request_resume_on_paused():
    st = LabState(status="paused", paused_at=mins(30))
    a = decide(T0, reg(), None, None, st, "resume", CFG)
    assert a.kind == "resume" and a.consumes_request


def test_moot_requests_are_consumed_without_action():
    st = LabState(status="paused", paused_at=mins(30))
    a = decide(T0, reg(), None, None, st, "pause", CFG)
    assert a.kind == "none" and a.consumes_request
    b = decide(T0, reg(), mins(1), None, None, "resume", CFG)
    assert b.kind == "none" and b.consumes_request


def test_dry_run_flag_is_set_on_actions():
    assert decide(T0, reg(), mins(130), None, None, None, DRY).dry_run is True
    assert decide(T0, reg(), mins(130), None, None, None, CFG).dry_run is False


def test_lab_in_error_is_left_alone_even_if_overdue():
    st = LabState(status="error", since=mins(5), last_error="boom")
    a = decide(T0, reg(destroy_after="2030-01-01"), mins(900), None, st, "pause", CFG)
    assert a.kind == "none"


@pytest.mark.parametrize("status", ["saving", "pausing", "resuming", "destroying"])
def test_in_progress_never_triggers_new_action(status):
    st = LabState(status=status, since=mins(5))
    assert decide(T0, reg(destroy_after="2030-01-01"), mins(900), None, st, "pause", CFG).kind == "none"


def test_destroyed_lab_ignored_but_reregistered_lab_is_fresh():
    st = LabState(status="destroyed", since=T0 - dt.timedelta(days=1))
    old = reg(registered_at=(T0 - dt.timedelta(days=2)).isoformat())
    assert decide(T0, old, mins(900), None, st, None, CFG).kind == "none"
    new = reg(registered_at=(T0 - dt.timedelta(hours=3)).isoformat())
    assert decide(T0, new, mins(10), None, st, None, CFG).kind == "none"
    assert decide(T0, new, mins(200), None, st, None, CFG).kind == "save_and_pause"


def test_config_validation():
    for bad in ({"idle_hours": 0}, {"warn_minutes": 120}, {"pause_destroy_days": 0}):
        with pytest.raises(ValueError):
            Config(**bad)


def test_action_rejects_unknown_kind():
    with pytest.raises(ValueError):
        Action("explode", "x")


# ------------------------------------------------------------ validation

def test_registration_validation():
    for bad in (reg_doc(lab_id="other"), reg_doc(destroy_after="tomorrow"), reg_doc(region=""),
                reg_doc(registered_at="nope"), reg_doc(tf_vars=[]), [1, 2]):
        with pytest.raises(ValueError):
            Registration.from_json(bad, LAB)


def test_state_validation():
    with pytest.raises(ValueError):
        LabState.from_json({"status": "weird"})
    with pytest.raises(ValueError):
        LabState.from_json([])


@pytest.mark.parametrize("lab", ["", "A", "-x", "x" * 42, "a b", "a/b", "a..b", "lab\n", "../x", "ok-lab_"])
def test_invalid_lab_ids(lab):
    assert not guard.valid_lab_id(lab)


def test_valid_lab_ids():
    assert guard.valid_lab_id("a") and guard.valid_lab_id("a" * 41) and guard.valid_lab_id("0-a-9")


def test_budget_message_mapping():
    assert guard.lab_from_budget_message("Budget Name: lab-one-monthly\nBudget Type: Cost") == "lab-one"
    assert guard.lab_from_budget_message("Budget Name: Other") is None
    assert guard.lab_from_budget_message("Budget Name: ../x-monthly") is None
    assert guard.lab_from_budget_message("nothing") is None
    assert guard.lab_from_budget_message(None) is None


# ------------------------------------------------------------ fakes

class FakeError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.deleted = []

    def put(self, key, doc):
        self.objects[key] = json.dumps(doc).encode() if not isinstance(doc, bytes) else doc

    def get_object(self, Bucket, Key):
        if Key not in self.objects:
            raise FakeError("NoSuchKey")
        return {"Body": io.BytesIO(self.objects[Key])}

    def put_object(self, Bucket, Key, Body, **kw):
        self.objects[Key] = Body

    def delete_object(self, Bucket, Key):
        self.objects.pop(Key, None)
        self.deleted.append(Key)

    def list_objects_v2(self, Bucket, Prefix, Delimiter=None, ContinuationToken=None):
        keys = sorted(k for k in self.objects if k.startswith(Prefix))
        if Delimiter:
            pre = sorted({Prefix + k[len(Prefix):].split("/")[0] + "/" for k in keys if "/" in k[len(Prefix):]})
            return {"CommonPrefixes": [{"Prefix": p} for p in pre]}
        return {"Contents": [{"Key": k} for k in keys]}

    def state(self, lab=LAB):
        return json.loads(self.objects[f"state/{lab}.json"])


class FakeSNS:
    def __init__(self):
        self.messages = []

    def publish(self, TopicArn, Subject, Message):
        self.messages.append((Subject, Message))


class FakeEC2:
    def __init__(self, ids=("i-bastion",)):
        self.ids = list(ids)

    def describe_instances(self, Filters):
        return {"Reservations": [{"Instances": [{"InstanceId": i} for i in self.ids]}]}


class FakeSSM:
    def __init__(self, status="InProgress"):
        self.status = status
        self.sent = []

    def send_command(self, **kw):
        self.sent.append(kw)
        return {"Command": {"CommandId": "cmd-1"}}

    def get_command_invocation(self, CommandId, InstanceId):
        return {"Status": self.status}


class FakeBuild:
    def __init__(self, status="IN_PROGRESS"):
        self.status = status
        self.started = []

    def start_build(self, **kw):
        self.started.append(kw)
        return {"build": {"id": f"proj:{len(self.started)}"}}

    def batch_get_builds(self, ids):
        return {"builds": [{"id": ids[0], "buildStatus": self.status}]}


def make(config=CFG, ec2_ids=("i-bastion",), ssm_status="InProgress", build_status="IN_PROGRESS"):
    g = Guard(s3=FakeS3(), ssm=FakeSSM(ssm_status), ec2=FakeEC2(ec2_ids), codebuild=FakeBuild(build_status),
              sns=FakeSNS(), bucket=BUCKET, notify_topic=TOPIC, budget_topic=BUDGET, project="proj",
              config=config, region="us-east-1")
    g.s3.put(f"labs/{LAB}/registration.json", reg_doc())
    return g


def action_of(g):
    return [kw["environmentVariablesOverride"][0]["value"] for kw in g.codebuild.started]


# ------------------------------------------------------------ handlers

def test_run_all_idle_lab_saves_then_pauses():
    g = make()
    g.s3.put(f"heartbeat/{LAB}", {"ts": mins(130).isoformat()})
    assert guard_summary(g)[LAB].startswith("save_and_pause")
    assert g.ssm.sent[0]["Parameters"]["commands"] == [f"/opt/lab/export.sh {LAB} {BUCKET}"]
    st = g.s3.state()
    assert st["status"] == "saving" and st["then"] == "pause"
    g.ssm.status = "Success"
    g.run_lab(LAB, T0 + dt.timedelta(minutes=15))
    assert action_of(g) == ["pause"] and g.s3.state()["status"] == "pausing"
    g.codebuild.status = "SUCCEEDED"
    g.run_lab(LAB, T0 + dt.timedelta(minutes=30))
    st = g.s3.state()
    assert st["status"] == "paused" and st["paused_at"] is not None


def guard_summary(g):
    return g.run_all(T0)


def test_warn_publishes_and_sets_warned():
    g = make()
    g.s3.put(f"heartbeat/{LAB}", {"ts": mins(95).isoformat()})
    guard_summary(g)
    assert g.s3.state()["status"] == "warned"
    assert "pausing soon" in g.sns.messages[0][0]
    guard_summary(g)
    assert len(g.sns.messages) == 1


def test_dry_run_emails_and_changes_nothing():
    g = make(DRY)
    g.s3.put(f"heartbeat/{LAB}", {"ts": mins(130).isoformat()})
    out = guard_summary(g)
    assert out[LAB].startswith("dry run")
    assert g.ssm.sent == [] and g.codebuild.started == []
    st = g.s3.state()
    assert st["status"] == "running" and st["last_run"] is not None
    assert "DRY RUN" in g.sns.messages[0][0]
    guard_summary(g)
    assert len(g.sns.messages) == 1  # not repeated every run


def test_dry_run_keeps_request():
    g = make(DRY)
    g.s3.put(f"requests/{LAB}.json", {"action": "pause", "ts": T0.isoformat()})
    guard_summary(g)
    assert f"requests/{LAB}.json" in g.s3.objects and g.ssm.sent == []


def test_pause_request_is_handled_and_deleted():
    g = make()
    g.s3.put(f"heartbeat/{LAB}", {"ts": mins(1).isoformat()})
    g.s3.put(f"requests/{LAB}.json", {"action": "pause", "ts": T0.isoformat()})
    guard_summary(g)
    assert g.s3.state()["status"] == "saving"
    assert f"requests/{LAB}.json" not in g.s3.objects


def test_resume_request_starts_resume_build():
    g = make()
    g.s3.put(f"state/{LAB}.json", {"status": "paused", "since": mins(60).isoformat(), "paused_at": mins(60).isoformat()})
    g.s3.put(f"requests/{LAB}.json", {"action": "resume", "ts": T0.isoformat()})
    guard_summary(g)
    assert action_of(g) == ["resume"] and g.s3.state()["status"] == "resuming"
    assert f"requests/{LAB}.json" not in g.s3.objects
    g.codebuild.status = "SUCCEEDED"
    g.run_lab(LAB, T0 + dt.timedelta(minutes=20))
    st = g.s3.state()
    assert st["status"] == "running" and st["resumed_at"] is not None


def test_invalid_request_is_deleted_and_reported():
    g = make()
    g.s3.put(f"requests/{LAB}.json", {"action": "explode"})
    out = guard_summary(g)
    assert out[LAB].startswith("error") and f"requests/{LAB}.json" not in g.s3.objects
    assert g.sns.messages


def test_save_without_bastion_is_an_error_not_a_pause():
    g = make(ec2_ids=())
    g.s3.put(f"heartbeat/{LAB}", {"ts": mins(500).isoformat()})
    out = guard_summary(g)
    assert out[LAB].startswith("error") and g.codebuild.started == []
    assert g.sns.messages


def test_failed_save_goes_to_error_and_emails():
    g = make()
    g.s3.put(f"heartbeat/{LAB}", {"ts": mins(500).isoformat()})
    guard_summary(g)
    g.ssm.status = "Failed"
    g.run_lab(LAB, T0 + dt.timedelta(minutes=15))
    st = g.s3.state()
    assert st["status"] == "error" and "save command Failed" in st["last_error"]
    assert g.codebuild.started == [] and g.sns.messages


def test_failed_build_goes_to_error():
    g = make()
    g.s3.put(f"state/{LAB}.json", {"status": "pausing", "since": mins(5).isoformat(), "build_id": "proj:9"})
    g.codebuild.status = "FAILED"
    g.run_lab(LAB, T0)
    assert g.s3.state()["status"] == "error"


def test_in_progress_does_not_start_second_build():
    g = make()
    g.s3.put(f"state/{LAB}.json", {"status": "pausing", "since": mins(90).isoformat(), "build_id": "proj:9"})
    g.s3.put(f"heartbeat/{LAB}", {"ts": mins(900).isoformat()})
    out = g.run_lab(LAB, T0)
    assert g.codebuild.started == [] and out.startswith("pausing")
    assert g.s3.state()["status"] == "pausing"


@pytest.mark.parametrize("status", ["saving", "pausing", "resuming", "destroying"])
def test_stuck_over_two_hours_sets_error_and_emails(status):
    g = make()
    g.s3.put(f"state/{LAB}.json", {"status": status, "since": (T0 - dt.timedelta(hours=2, minutes=1)).isoformat(),
                                   "build_id": "proj:9", "command_id": "c", "instance_id": "i-1"})
    g.run_lab(LAB, T0)
    st = g.s3.state()
    assert st["status"] == "error" and "2 hours" in st["last_error"]
    assert g.codebuild.started == [] and g.ssm.sent == [] and len(g.sns.messages) == 1


def test_exactly_two_hours_is_not_yet_stuck():
    g = make()
    g.s3.put(f"state/{LAB}.json", {"status": "pausing", "since": (T0 - dt.timedelta(hours=2)).isoformat(),
                                   "build_id": "proj:9"})
    g.run_lab(LAB, T0)
    assert g.s3.state()["status"] == "pausing"


def test_lab_in_error_is_not_touched_by_run():
    g = make()
    g.s3.put(f"state/{LAB}.json", {"status": "error", "since": mins(5).isoformat(), "last_error": "x"})
    g.s3.put(f"heartbeat/{LAB}", {"ts": mins(900).isoformat()})
    out = g.run_lab(LAB, T0)
    assert out.startswith("none") and g.ssm.sent == [] and g.codebuild.started == []


def test_invalid_lab_id_never_acted_on():
    g = make()
    g.s3.put("labs/Bad_Lab/registration.json", reg_doc(lab_id="Bad_Lab"))
    g.s3.put("labs/../registration.json", reg_doc())
    assert guard_summary(g).get("Bad_Lab") == "skipped: invalid lab id"
    assert g.run_lab("x/../y", T0) == "skipped: invalid lab id"
    assert g.run_lab("lab\n", T0) == "skipped: invalid lab id"


def test_no_registration_no_action():
    g = make()
    del g.s3.objects[f"labs/{LAB}/registration.json"]
    g.s3.put(f"heartbeat/{LAB}", {"ts": mins(900).isoformat()})
    assert g.run_lab(LAB, T0) == "skipped: no registration"
    assert g.ssm.sent == []


def test_wrong_region_registration_is_refused():
    g = make()
    g.s3.put(f"labs/{LAB}/registration.json", reg_doc(region="eu-west-1"))
    g.s3.put(f"heartbeat/{LAB}", {"ts": mins(900).isoformat()})
    out = g.run_lab(LAB, T0)
    assert out.startswith("error") and g.ssm.sent == []


def test_bad_heartbeat_json_fails_safe_without_pausing():
    g = make()
    g.s3.put(f"heartbeat/{LAB}", b"{not json")
    out = g.run_lab(LAB, T0)
    assert out.startswith("error") and g.ssm.sent == [] and g.sns.messages
    n = len(g.sns.messages)
    g.s3.put(f"state/{LAB}.json", {"status": "running", "since": mins(5).isoformat()})
    g.run_lab(LAB, T0)
    g.run_lab(LAB, T0)
    assert len(g.sns.messages) == n + 1  # same error recorded once, not every run


def test_destroy_after_passed_saves_then_destroys():
    g = make()
    g.s3.put(f"labs/{LAB}/registration.json", reg_doc(destroy_after="2030-01-01"))
    g.s3.put(f"heartbeat/{LAB}", {"ts": mins(1).isoformat()})
    guard_summary(g)
    assert g.s3.state()["then"] == "destroy"
    g.ssm.status = "Success"
    g.run_lab(LAB, T0 + dt.timedelta(minutes=15))
    assert action_of(g) == ["destroy"]
    g.codebuild.status = "SUCCEEDED"
    g.run_lab(LAB, T0 + dt.timedelta(minutes=30))
    assert g.s3.state()["status"] == "destroyed"


def test_paused_lab_destroy_skips_save():
    g = make()
    g.s3.put(f"state/{LAB}.json", {"status": "paused", "since": (T0 - dt.timedelta(days=8)).isoformat(),
                                   "paused_at": (T0 - dt.timedelta(days=8)).isoformat()})
    guard_summary(g)
    assert g.ssm.sent == [] and action_of(g) == ["destroy"]


def test_destroyed_lab_with_vanished_registration_is_finalised_from_state():
    g = make()
    del g.s3.objects[f"labs/{LAB}/registration.json"]
    g.s3.put(f"state/{LAB}.json", {"status": "destroying", "since": mins(10).isoformat(), "build_id": "proj:3"})
    g.codebuild.status = "SUCCEEDED"
    guard_summary(g)
    assert g.s3.state()["status"] == "destroyed"


# ------------------------------------------------------------ spend limit

def budget_event(message, topic=BUDGET):
    return {"Records": [{"Sns": {"TopicArn": topic, "Message": message}}]}


def test_spend_notification_starts_destroy_for_that_lab_only():
    g = make()
    g.s3.put(f"state/{LAB}.json", {"status": "paused", "since": mins(60).isoformat(), "paused_at": mins(60).isoformat()})
    out = g.run_budget(budget_event(f"Budget Name: {LAB}-monthly\nThreshold: 100"), T0)
    assert out[LAB].startswith("destroy") and action_of(g) == ["destroy"]
    assert g.codebuild.started[0]["environmentVariablesOverride"][1]["value"] == LAB


def test_spend_on_running_lab_saves_first():
    g = make()
    g.run_budget(budget_event(f"Budget Name: {LAB}-monthly"), T0)
    assert g.s3.state()["status"] == "saving" and g.s3.state()["then"] == "destroy"


def test_spend_respects_dry_run():
    g = make(DRY)
    out = g.run_budget(budget_event(f"Budget Name: {LAB}-monthly"), T0)
    assert out[LAB].startswith("dry run") and g.ssm.sent == [] and g.codebuild.started == []


def test_spend_ignores_unregistered_wrong_topic_and_bad_names():
    g = make()
    assert g.run_budget(budget_event("Budget Name: ghost-monthly"), T0) == {"ghost": "skipped: no registration"}
    assert g.run_budget(budget_event(f"Budget Name: {LAB}-monthly", topic="arn:other"), T0) == {}
    assert g.run_budget(budget_event("Budget Name: ../x-monthly"), T0) == {}
    assert g.ssm.sent == [] and g.codebuild.started == []


def test_spend_skips_lab_already_being_destroyed():
    g = make()
    g.s3.put(f"state/{LAB}.json", {"status": "destroying", "since": mins(5).isoformat(), "build_id": "p:1"})
    out = g.run_budget(budget_event(f"Budget Name: {LAB}-monthly"), T0)
    assert out[LAB].startswith("skipped") and g.codebuild.started == []


# ------------------------------------------------------------ entry

def test_config_from_env_defaults_to_dry_run():
    assert guard.config_from_env({}).dry_run is True
    assert guard.config_from_env({"DRY_RUN": "false"}).dry_run is False
    assert guard.config_from_env({"DRY_RUN": "banana"}).dry_run is True

from __future__ import annotations

import json

from labcli.terraform import COST_WARNING, DESTROY_WARNING, apply_argv, destroy_argv, init_argv, outputs_to_env


def test_argv_shapes() -> None:
    assert init_argv() == ("bash", "/lab/terraform/scripts/lab-init.sh")
    assert "-auto-approve" in apply_argv()
    assert not any(a.startswith("-state=") for a in apply_argv())
    assert destroy_argv()[2] == "destroy" and "-auto-approve" in destroy_argv()


def test_warnings_are_ascii_and_loud() -> None:
    for text in (COST_WARNING, DESTROY_WARNING):
        assert text.isascii()
    assert "lab down" in COST_WARNING
    assert "WARNING" in DESTROY_WARNING


def test_outputs_to_env_filters_to_contract() -> None:
    raw = json.dumps({
        "kms_key_arn": {"value": "arn:x"},
        "vpc_id": {"value": "vpc-1"},
        "random_thing": {"value": "no"},
        "LOKI_PASSWORD": {"value": "pw", "sensitive": True},
    })
    assert outputs_to_env(raw) == {"KMS_KEY_ARN": "arn:x", "VPC_ID": "vpc-1", "LOKI_PASSWORD": "pw"}


def test_outputs_to_env_bad_json() -> None:
    assert outputs_to_env("not json") == {}
    assert outputs_to_env("[]") == {}

"""Terraform argv builders, warnings, and output handling for lab up/down."""
from __future__ import annotations

import json

from labcli.environment import CONTAINER_PLATFORM, CONTAINER_TERRAFORM, CONTRACT_VARS

_CHDIR = f"-chdir={CONTAINER_TERRAFORM}"

COST_WARNING = """\
COST WARNING: 'lab up' builds a real OpenShift cluster and supporting
resources in your AWS account (compute, NAT gateway, Elastic IP, load
balancing, KMS key, S3 storage). They are billed until they are destroyed.
When you stop working, run 'lab down'. Closing this window does NOT stop
the charges."""

DESTROY_WARNING = """\
==================================================================
WARNING: 'lab down' DESTROYS your whole lab in AWS.
Everything in the cluster, the KMS key and the buckets will be removed.
Run it whenever you stop working: the lab bills until it is destroyed.
=================================================================="""

PULL_SECRET_HELP = """'lab up' also installs the cluster, which needs your Red Hat pull secret.
Download it from your Red Hat account, save it as a file INSIDE your lab workspace
({workspace}), and set PULL_SECRET_FILE to that file's path. Optional: BASE_DOMAIN
(default: your only public Route 53 hosted zone) and SSH_PUBLIC_KEY_FILE (also under
the workspace). To build only the AWS infrastructure, use 'lab up --skip-cluster'."""

CLUSTER_FAILED = """The AWS infrastructure is built, but the cluster install did not finish.
It may still be running on the bastion. Run 'lab up' again to keep waiting,
or 'lab down' to remove everything. The lab is billing until 'lab down' finishes."""

CLUSTER_DESTROY_FAILED = """!!! THE CLUSTER WAS NOT CONFIRMED DESTROYED, SO TERRAFORM DESTROY WAS NOT RUN !!!
The lab is STILL RUNNING and still billing. Fix the problem above, then run
'lab down' again. If the lab is paused, run 'lab resume' first."""

DOWN_FAILED = """\
!!! THE LAB MAY STILL BE RUNNING AND STILL BILLING !!!
Destroy did not finish. Run 'lab down' again. If it keeps failing, open the
AWS console and delete the resources tagged with your lab id by hand."""


def init_argv() -> tuple[str, ...]:
    """Create the state key and bucket if needed, then init the S3 backend (terraform/scripts/lab-init.sh)."""
    return ("bash", f"{CONTAINER_TERRAFORM}/scripts/lab-init.sh")


def install_argv() -> tuple[str, ...]:
    """Render install-config.yaml, hand it to the bastion, wait for the cluster (terraform/scripts/lab-install.sh)."""
    return ("bash", f"{CONTAINER_TERRAFORM}/scripts/lab-install.sh")


def platform_argv(only: str | None = None) -> tuple[str, ...]:
    """Install the in-lab services (Gitea, Loki, Grafana, ...) with lab/platform/install.sh."""
    argv = ("bash", f"{CONTAINER_PLATFORM}/install.sh")
    return argv + (("--only", only) if only else ())


def cluster_destroy_argv() -> tuple[str, ...]:
    """Put the install/destroy marker and wait for status destroyed, before terraform destroy."""
    return ("bash", f"{CONTAINER_TERRAFORM}/scripts/lab-install.sh", "destroy")


def apply_argv() -> tuple[str, ...]:
    return ("terraform", _CHDIR, "apply", "-input=false", "-auto-approve")


def destroy_argv() -> tuple[str, ...]:
    return ("terraform", _CHDIR, "destroy", "-input=false", "-auto-approve")


def output_argv() -> tuple[str, ...]:
    return ("terraform", _CHDIR, "output", "-json")


def outputs_to_env(raw_json: str) -> dict[str, str]:
    """Map terraform outputs onto contract variable names. Ignores everything else."""
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    allowed = set(CONTRACT_VARS)
    result: dict[str, str] = {}
    for key, entry in data.items():
        name = str(key).upper()
        if name in allowed and isinstance(entry, dict) and "value" in entry:
            result[name] = str(entry["value"])
    return result

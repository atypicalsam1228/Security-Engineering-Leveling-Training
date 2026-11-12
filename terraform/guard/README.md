# Lab cost guard

STATUS: written to the contract in `COST-CONTROLS.md`. Nothing here has run on AWS. It ships with `dry_run = true`.

The guard is a once-per-account-and-region stack, separate from any lab, so destroying a lab never removes it. It pauses idle labs, destroys labs that stay paused too long, hit their spend limit or pass `destroy_after`, and emails what it does. Every action applies to one lab only.

## What it creates

- S3 bucket `lab-guard-<account>-<region>`: versioned, SSE-S3, public access blocked, TLS only. Lifecycle: `saves/` expires after 90 days, `heartbeat/` and `requests/` after 7, other noncurrent versions after 30. Holds the contract keys (`labs/`, `heartbeat/`, `keep/`, `requests/`, `state/`, `saves/`, `code/`).
- SNS `lab-guard-notify` (email subscription to `alert_email`) and `lab-guard-budget` (policy lets `budgets.amazonaws.com` publish from this account; the Lambda is subscribed).
- Lambda `lab-guard` (`lambda/guard.py`, Python 3.13, boto3 only) on an EventBridge schedule.
- CodeBuild project `lab-guard-runner` (`buildspec.yml`): `ACTION` = `pause`, `resume` or `destroy`, plus `LAB_ID`. Terraform 1.14.8 is pinned with its sha256.
- `code/terraform.zip`: the lab Terraform (parent directory) without `guard/`, `sweeper/`, `.terraform`, state, `*.tfvars*` and `*.zip`.
- IAM roles `lab-guard-lambda` and `lab-guard-codebuild`.

Extensions to the state file contract (needed for polling): `resumed_at`, `command_id`, `instance_id`, `build_id`, `then`. `last_notice` is `{kind, ts}`.

## Behaviour

- Idle = no heartbeat, `keep` or resume for `idle_hours`. Missing heartbeat counts from `registered_at`. `build_grace_hours` after registration protects a lab under construction. Warn at `idle_hours - warn_minutes`, pause at `idle_hours`. A schedule coarser than `warn_minutes` can skip the warning.
- Pause and destroy of a running lab first run `/opt/lab/export.sh <LAB_ID> <guard_bucket>` on the bastion (tag `LabId`, `Role=openshift-install-fips`; the Role tag value is read from `bastion.tf`, not verified on AWS). If no running bastion exists, or the save fails, the lab goes to `error` and nothing is paused or destroyed. A paused lab was saved when it paused, so its destroy skips the save.
- One lab in `saving`, `pausing`, `resuming` or `destroying` never gets a second build. After more than 2 hours in that state it is set to `error` and emailed. The CodeBuild timeout is 100 minutes.
- `error` is terminal until an operator fixes the cause and edits or deletes `state/<LAB_ID>.json`. Failures are recorded in `last_error` and emailed once per distinct message.
- Invalid `LAB_ID` (must match `^[a-z0-9][a-z0-9-]{0,40}$`), invalid S3 JSON, a registration for another region, or a lab without `registration.json` are never acted on. A bad heartbeat or keep file raises an error rather than being treated as idle.
- Spend limit: the budget message must name `<lab_id>-monthly`; the SNS record must come from the budget topic. The AWS Budgets message text format is not verified.
- Emails go to the guard's `alert_email` topic, not to each learner: SNS cannot mail an unsubscribed address, so the learner `alert_email` in the registration is not used.

## Deploy (once per account and region)

```
cd terraform/guard
terraform init
terraform apply -var region=us-east-1 -var alert_email=ops@example.invalid
```

Confirm the SNS subscription email. Pass `terraform output -raw guard_bucket` to each lab as `guard_bucket`, and `budget_topic_arn` to the lab budget notification. Variables: `region`, `alert_email`, `idle_hours` (2), `warn_minutes` (30), `build_grace_hours` (2), `pause_destroy_days` (7), `schedule` (`rate(15 minutes)`), `dry_run` (true), `spend_destroy_pct` (100, informational here; the lab sets the real threshold). Validation rejects `idle_hours < 1`, `warn_minutes >= idle_hours * 60` and `pause_destroy_days < 1`. Re-apply the guard whenever the lab Terraform changes, so `code/terraform.zip` is current.

## Test safely, then turn off dry_run

1. Leave `dry_run = true`. Register one throwaway lab and open `lab shell`; close it. After the idle window the guard emails "DRY RUN ... would save_and_pause" and changes nothing except `state/<LAB_ID>.json` `last_run`. Dry-run emails repeat at most every 6 hours per action.
2. Invoke the Lambda by hand in the console to avoid waiting for the schedule.
3. Run the real path on the throwaway lab only: `terraform apply -var dry_run=false ...`, then `lab pause`, check the save under `saves/`, the paused state, `lab resume`, and finally `lab down` or a short `destroy_after`.
4. Keep `dry_run=false` only once pause, resume and destroy have each worked once.

## The CodeBuild role is broad

`lab-guard-codebuild` carries service-wide permissions (EC2, ELB, IAM, KMS, S3, Route 53, Budgets, SSM, logs, events, SNS, tagging). It has to, because it runs `terraform apply` and `terraform destroy` of a whole lab and `sweep.sh`, which destroys an OpenShift cluster whose resources the installer created and which cannot be listed in advance. It is effectively lab-wide admin. Explicit denies block creating IAM users, access keys, Organizations and account changes, and editing the guard's own roles or bucket policy. Deploy the guard only in a dedicated lab account, never one that holds other workloads. The Lambda role is narrow: S3 on the guard bucket prefixes, EC2 describe, SSM `SendCommand` to instances carrying a `LabId` tag (condition `ssm:resourceTag/LabId`, unverified) and the `AWS-RunShellScript` document, `StartBuild`/`BatchGetBuilds` on the one project, SNS publish to the notify topic. EC2 stop/start is done only by CodeBuild.

## Known limits

- A paused lab still bills about $0.35 a day (estimate). Use `lab down` for zero.
- Billing data lags by hours; the spend limit is a backstop, not a hard cap.
- A stopped single-node cluster may need certificate requests approved after a long pause; unverified.
- The log bucket (Object Lock, compliance mode) cannot be deleted before its retention ends.
- Nothing here has run on AWS.

More, specific to this stack: a destroy of a paused lab recreates the bastion and relies on it being able to destroy a cluster the earlier bastion created (installer metadata location unverified). `terraform destroy` of the lab stops at the Object Lock log bucket until retention ends, which leaves the build failed and the lab in `error`. The versioned guard bucket needs its versions removed before it can be destroyed. The build image `aws/codebuild/amazonlinux-x86_64-standard:5.0` and its tools (aws, jq, unzip) are assumed, not checked.

## Cost of the guard itself (ESTIMATE, not measured)

Idle guard with a handful of labs: Lambda about 2,900 runs a month (inside the free tier or cents), S3 requests and storage cents, log storage cents, SNS free tier. Roughly $1 a month or less. Each pause, resume or destroy build runs on a medium CodeBuild instance, about $0.01 a minute (rate from memory, unconfirmed), so roughly $0.10 to $1 per build depending on length. Compare with the lab it protects: the instance alone is about $0.77 an hour.

## Tests

```
cd terraform/guard
python -m pytest -q tests
terraform init -backend=false && terraform validate && terraform fmt -check
```

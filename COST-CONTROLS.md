# Cost Controls: Idle Pause, Spend Limit and Deadline

STATUS: DESIGN AND BUILD SPEC. Nothing here has run on AWS. Every figure is an estimate. The guard ships with `dry_run = true`: it emails what it would do and acts on nothing until an operator sets `dry_run = false` after a first successful test.

Goal: a learner who forgets to stop their lab does not keep paying for it. Each learner has their own lab (own `LAB_ID`, own cluster). Every action below applies to one lab only.

## 1. The tiers

| Tier | Trigger | Action | What still bills |
|---|---|---|---|
| 1 Warn | Idle for `idle_hours - warn_minutes` | Email the learner. `lab keep` extends. | Everything (lab running) |
| 2 Save and pause | No activity for `idle_hours` (default 2) | Save lab files to the guard bucket, stop the cluster instance, delete the bastion, NAT gateway, its Elastic IP and the SSM endpoints | Node disk, KMS key, S3 (about $0.35 a day, estimate) |
| 3 Destroy | Paused for `pause_destroy_days` (default 7), or the lab's spend limit is crossed, or `destroy_after` date passes | Save, then destroy the cluster and all lab infrastructure | Log bucket (Object Lock keeps it until retention ends), KMS key in its 7-day deletion window, the guard bucket (small) |
| Manual | `lab pause`, `lab resume`, `lab down` | Learner choice | `lab down` is the existing full destroy |

Activity means a heartbeat from an open `lab shell`, or a `lab keep`, or `lab resume`. A lab under construction is protected by `build_grace_hours` (default 2) after registration.

## 2. Parts and who builds them

| Part | Path | Notes |
|---|---|---|
| Guard stack (once per AWS account and region, outside any lab) | `terraform/guard/` | Bucket, SNS topic with email subscription, Lambda, scheduled rule, CodeBuild project, IAM. Survives lab destroys. |
| Lab Terraform changes | `terraform/*.tf`, `terraform/templates/`, `terraform/scripts/sweep.sh` | `paused` variable, lab registration, budget filter and notification, learner permissions, export script. |
| Lab command | `lab/labcli/`, `lab/tests/` | `lab keep`, `lab pause`, `lab resume`, `lab pull`, status line, heartbeat during `lab shell`. |
| Tool rows | `generators/tool_links.py` | Separate task. |

## 3. Contract between the parts (do not deviate)

Guard bucket (name from the guard stack output `guard_bucket`; passed to the lab as Terraform variable `guard_bucket`, default "" which disables everything below; exported to the learner as `GUARD_BUCKET`). Keys, all JSON unless noted, timestamps ISO 8601 UTC:

| Key | Written by | Content |
|---|---|---|
| `labs/<LAB_ID>/registration.json` | lab Terraform (`aws_s3_object`) | `{lab_id, region, state_bucket, state_key, state_kms_key_arn, destroy_after, alert_email, registered_at, tf_vars: {...}}` |
| `heartbeat/<LAB_ID>` | `lab shell` every 10 minutes while open | `{"ts": "..."}` |
| `keep/<LAB_ID>` | `lab keep [HOURS]` (default 4, max 24) | `{"until": "..."}` |
| `requests/<LAB_ID>.json` | `lab pause` / `lab resume` | `{"action": "pause" or "resume", "ts": "..."}`; the guard deletes it when handled |
| `state/<LAB_ID>.json` | guard Lambda only | `{status, since, paused_at, last_notice, last_error, last_run}`; status is one of `running`, `warned`, `saving`, `pausing`, `paused`, `resuming`, `destroying`, `destroyed`, `error` |
| `saves/<LAB_ID>/<UTC timestamp>/` | bastion `export.sh` | `gitea/<repo>.bundle`, `cluster/<namespace>.yaml`, `MANIFEST.json`, `restore.sh` |
| `code/terraform.zip` | guard stack (`archive_file` of `../`) | lab Terraform for CodeBuild |

Guard Lambda (`terraform/guard/lambda/guard.py`), runs every `schedule` (default `rate(15 minutes)`):
- Pure function `decide(now, registration, heartbeat, keep, state, request, config) -> Action` where Action is one of `none`, `warn`, `save_and_pause`, `resume`, `destroy`, with a reason string. It has no AWS calls and is unit tested for every tier, `keep`, `build_grace_hours`, a missing heartbeat, `dry_run`, and a lab in `error`.
- Handlers perform the action: `warn` publishes to SNS. `save_and_pause` runs SSM Run Command on the lab's bastion (tag `LabId`; document `AWS-RunShellScript`, command `/opt/lab/export.sh <LAB_ID> <guard_bucket>`), waits (next invocations poll status, never sleep long), then starts CodeBuild with `ACTION=pause`. `resume` starts CodeBuild with `ACTION=resume`. `destroy` starts CodeBuild with `ACTION=destroy`. Budget notifications arrive on the same SNS topic type described below.
- `dry_run=true`: compute and email the action, change nothing, write `last_run` only.
- Spend limit: the lab's budget notification (100 percent ACTUAL by default, variable `spend_destroy_pct`) publishes to the guard's budget SNS topic; the Lambda is subscribed; the budget name is `<lab_id>-monthly`; the Lambda maps it to the lab and starts `destroy` (still subject to `dry_run`).
- Never acts on a lab without `registration.json`, on an invalid `LAB_ID` (must match `^[a-z0-9][a-z0-9-]{0,40}$`), or on another account.

CodeBuild project (buildspec in `terraform/guard/`), environment variables `ACTION` (`pause`, `resume`, `destroy`) and `LAB_ID`:
- Fetches `code/terraform.zip` and `labs/<LAB_ID>/registration.json`, runs `terraform init` with the registered backend settings.
- `pause`: stop the cluster instances (tag `LabId`, excluding the bastion), then `terraform apply -auto-approve -var paused=true` with the registered `tf_vars`.
- `resume`: `terraform apply -auto-approve -var paused=false`, then start the cluster instances and wait for them to report running.
- `destroy`: if paused, apply `paused=false` first (recreates the bastion the installer destroy runs from), then `terraform/scripts/sweep.sh --apply --force --lab <LAB_ID>` (cluster first, then `terraform destroy`). Writes `state` accordingly.
- Terraform version pinned in the buildspec with its sha256.

Lab Terraform:
- `variable "paused"` (bool, default false). When true, no `aws_nat_gateway`, no NAT `aws_eip`, no route to the NAT, no SSM `aws_vpc_endpoint`, no bastion `aws_instance` (use `count`). Everything else, including disks, subnets, key, buckets and DNS, stays. The cluster instance is not Terraform's (the installer makes it); the guard stops and starts it.
- `variable "guard_bucket"` (string, default ""). When set: write `registration.json`; add learner permissions (below); set output `GUARD_BUCKET`; add the `export.sh` script to the bastion user data.
- Learner permissions (in `iam_learner_guard.tf`): `s3:PutObject` on `heartbeat/<lab_id>`, `keep/<lab_id>` and `requests/<lab_id>.json`; `s3:GetObject` on `state/<lab_id>.json` and `saves/<lab_id>/*`; `s3:ListBucket` limited by prefix condition. Nothing for any other lab.
- Budget: add a `cost_filter` on the `LabId` cost allocation tag (needs the tag activated once in the billing console; note this in the README), keep the existing email notifications, add a notification to the guard's budget SNS topic at `spend_destroy_pct` of `budget_limit_usd` when `guard_bucket` is set.
- `export.sh`: runs on the bastion, with the installer directory's kubeconfig. Saves the Gitea repositories as git bundles (via the in-cluster Gitea API or `oc exec`; unverified, say so), and `oc get -o yaml` of the lab namespaces (`demo`, `build`, `siem`, `chat`, `gitea`, `keycloak`, `kyverno`, `security-tools` minus Secret data), writes `MANIFEST.json` and a `restore.sh`, and uploads to `saves/<lab_id>/<timestamp>/`. Secrets are never exported.
- `sweep.sh --force` is only valid together with `--lab` and skips the expired-date check; everything else about it (account check, `SWEEP_ACCOUNT_ID`) stays.

Lab command (`lab`): new subcommands `keep [HOURS]`, `pause`, `resume`, `pull [--latest|--list]`; `status` shows the guard state, last heartbeat and time until pause (or "guard not configured"); `shell` writes a heartbeat at start and every 10 minutes while open (a thread that runs `aws s3api put-object` in a one-off tools container; failures are logged once, never block the shell). `pull` copies `saves/<LAB_ID>/<latest>/` to `~/lab-workspace/saves/`. All of these print a clear message and exit non-zero without `GUARD_BUCKET`. `GUARD_BUCKET` is added to the contract variables in `lab/labcli/environment.py`. `lab down` still destroys everything at once and writes nothing to the guard; since the cluster step was added it first asks the bastion to destroy the cluster (`install/destroy` marker, waits up to 60 minutes, an estimate) and only then runs `terraform destroy`. A paused lab has no bastion, so run `lab resume` before `lab down`; the guard's own destroy action already resumes first, as described above.

## 4. Variables (guard stack)

`region`, `alert_email`, `idle_hours` (2), `warn_minutes` (30), `build_grace_hours` (2), `pause_destroy_days` (7), `schedule` (`rate(15 minutes)`), `dry_run` (true), `spend_destroy_pct` (100). Lab variables: `paused`, `guard_bucket`, `spend_destroy_pct`.

## 5. Known limits (state them in the READMEs)

- A paused lab still bills about $0.35 a day (estimate). Use `lab down` for zero.
- Billing data lags by hours; the spend limit is a backstop, not a hard cap.
- A stopped single-node cluster may need certificate requests approved after a long pause; unverified.
- The log bucket (Object Lock, compliance mode) cannot be deleted before its retention ends.
- Nothing here has run on AWS.

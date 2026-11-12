# lab: training lab command

One command-line tool for the hands-on modules. Works on Mac and Windows.

## Install

1. Install Python 3.10 or newer and either podman or docker.
2. Build the tools image with `python lab.py build-image` (see image/README.md). It holds oc, kubectl, jq, curl, git, openssl, terraform, aws,
   python3, cosign, trivy, tkn, argocd, session-manager-plugin. Set `LAB_IMAGE` to its name
   (default: `lab-tools:latest`).
3. Run the tool from this folder: `python lab.py <command>`
   Or install it: `pip install -e ./lab` and then run `lab <command>`.
4. Put your AWS credentials in your normal environment (for example AWS_PROFILE).
   They are passed into the container by name. Passwords and tokens are never printed.

## Commands

| Command | What it does |
|---|---|
| `lab modules` | List modules in the recommended order. |
| `lab up [--skip-cluster]` | Build your lab in AWS with Terraform, then install the cluster with `terraform/scripts/lab-install.sh` and save the kubeconfig to `<workspace>/.lab/kubeconfig`. Costs money. Asks you to type `yes`. `--skip-cluster` stops after the infrastructure. |
| `lab down` | Destroy the cluster first (marker `install/destroy`, waits for status `destroyed`), then the AWS infrastructure. Run it every time you stop. Asks you to type `destroy`. |
| `lab platform [--only NN]` | Install the in-lab services (scripts in `lab/platform/`, see its README). Run by `lab up`; safe to repeat. |
| `lab shell` | Open the tools container with your workspace and lab variables. Module steps run inside it; `lab` itself is installed on your computer only, so `lab start`, `lab reset` and `lab down` are typed outside it. |
| `lab start <module>` | Load the module's starting state (example: `lab start grc-2`). |
| `lab reset <module>` | Return the module to its starting state. |
| `lab keep [HOURS]` | Tell the cost guard you are still working: no idle pause for HOURS (default 4, 1 to 24). |
| `lab pause [--no-wait]` | Save your lab files and pause the lab now. Cheaper, not free. Waits up to 30 minutes for the guard (checks about every 15 minutes). |
| `lab resume [--no-wait]` | Bring a paused lab back. Also counts as activity. |
| `lab pull [--latest\|--list]` | Copy the newest save (git bundles, namespace YAML without Secrets) to `<workspace>/saves/<timestamp>/`, or list saves. |
| `lab build-image` | Build the tools container image locally from `image/Dockerfile`. |
| `lab status` | Show engine, workspace, which lab variables are set, modules applied, any fault still active. |

Every command that changes something accepts `--dry-run`, which prints what would run and
changes nothing. `up` and `down` also accept `--yes` to skip the question.

## Cluster install inputs (`lab up`)

Set these in your normal environment before `lab up` (nothing is stored by `lab`):

| Variable | Needed | Meaning |
|---|---|---|
| `PULL_SECRET_FILE` | yes | Your Red Hat pull secret file. It must be under the workspace (default `~/lab-workspace`) because only that folder is mounted into the tools container; `lab` translates the path (Windows paths included) to `/workspace/...`. `lab up` checks this before building anything and stops with a message if it is unset, missing or outside the workspace. The secret is never printed. |
| `BASE_DOMAIN` | no | Route 53 base domain. Default: the only public hosted zone in the account. |
| `SSH_PUBLIC_KEY_FILE` | no | Public key file under the workspace. Default: a fresh key pair, public half only. |

`lab up --dry-run` prints every step, including the install step with the translated path, and notes anything missing.
If the install fails or times out, `lab up` says so and the lab is still billing: run `lab up` again to keep waiting or `lab down`. Nothing here has run on AWS.

## Cost: read this

`lab up` creates billable AWS resources. They keep billing until `lab down` finishes.
Closing your laptop does not stop them. After `lab down`, confirm in the AWS console that
nothing tagged with your lab id remains.

## Cost guard (idle pause)

If the lab was built with a guard bucket, `GUARD_BUCKET` is one of your lab variables and
the guard looks after forgotten labs: it warns you, then saves and pauses an idle lab, and
eventually destroys it (see COST-CONTROLS.md). While `lab shell` is open it writes a
heartbeat at start and every 10 minutes (a failure is reported once and never stops the
shell). `lab status` shows the guard state, your last heartbeat and an estimated time until
pause (it assumes the default 2 idle hours). Without `GUARD_BUCKET` the guard commands print
a message and exit non-zero.

Limits: a paused lab still bills about $0.35 a day (estimate). **`lab down` is the way to
stop all billing.** `keep`, `pause`, `resume` and `pull` run from your own computer, not
inside `lab shell`. Nothing here has run on AWS yet.

## How check works

Each module's verify commands run in the tools container (or directly if you are already
inside `lab shell`). If the module's expected output starts with "Example only", the check
compares the stable labels on each expected line (the text before a colon or tab) and
ignores values and placeholders. Otherwise it compares the output exactly, ignoring
spacing. A few tests need a manual step (for example saving a file first); the module text
says so.

## Settings (optional environment variables)

`LAB_IMAGE`, `LAB_ENGINE` (podman or docker), `LAB_WORKSPACE` (default `~/lab-workspace`),
`LAB_STATES_DIR`, `LAB_TERRAFORM_DIR`, `LAB_GENERATORS_DIR`.

## For maintainers

Module data and tests are read from `../generators/content` (read only). Start states live
in `states/<module-id>/`: ordered `.sh` scripts (idempotent) and `.yaml` manifests
(`oc apply`), `reset.d/` for reset-only steps, `README.md`, and `TODO.md` where the lab
build must still supply something. Run tests: `pytest --cov=labcli`.

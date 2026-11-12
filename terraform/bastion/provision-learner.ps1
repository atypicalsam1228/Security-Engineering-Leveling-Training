<#
Builds and hands over one learner's lab. Run it yourself, on your own computer, once per learner.
Learners never run lab up or lab down and have no AWS account.

  Step 1, build the learner's own lab (about an hour, bills until lab down):
    . $HOME\lab-workspace\lab-env.ps1
    Use-LabAws
    .\provision-learner.ps1 -LabId eng-l1 -Action Build

  Step 2, hand it over (after the access bastion is applied and the lab is up):
    .\provision-learner.ps1 -LabId eng-l1 -Action Deliver -BastionHost <bastion public ip>

  Step 3, tear down at the end of the day:
    .\provision-learner.ps1 -LabId eng-l1 -Action Down

Each learner gets their own workspace folder, so their lab files never mix with yours.
Deliver is untested: the access bastion did not exist when this was written.
#>
param(
    [Parameter(Mandatory)][ValidatePattern('^eng-l[1-3]$')][string]$LabId,
    [Parameter(Mandatory)][ValidateSet('Build', 'Deliver', 'Down')][string]$Action,
    [string]$BastionHost,
    [string]$DestroyAfter,      # YYYY-MM-DD: the guard destroys the lab once this date has passed (UTC)
    [int]$KeepHours = 12,       # the guard will not pause the lab for idleness for this long
    [string]$BudgetLimitUsd = '12',   # spend limit for this lab; the guard destroys it when spend reaches the limit
    [string]$AlertEmail = $env:LAB_ALERT_EMAIL
)

$ErrorActionPreference = 'Stop'
foreach ($name in 'LAB_ALERT_EMAIL', 'LAB_BASE_DOMAIN', 'LAB_AWS_ACCOUNT_ID') {
    if (-not [Environment]::GetEnvironmentVariable($name)) { throw "Set $name before running this script." }
}
$Project   = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Home1     = "$HOME\lab-workspaces\$LabId"      # one workspace per learner lab
$KeyFile   = "$HOME\lab-workspace\learner-keys\$LabId"
$PullSrc   = "$HOME\lab-workspace\pull-secret.txt"
$SshOpts   = @('-i', $KeyFile, '-o', 'StrictHostKeyChecking=accept-new')

function Require-AwsKeys {
    if (-not $env:AWS_ACCESS_KEY_ID) {
        throw 'No AWS keys in this window. Run: . $HOME\lab-workspace\lab-env.ps1 ; Use-LabAws'
    }
}

function Set-LabEnvironment {
    New-Item -ItemType Directory -Force $Home1 | Out-Null
    Copy-Item $PullSrc "$Home1\pull-secret.txt" -Force     # the installer reads it from inside the workspace
    # Each lab needs its own copy of the Terraform folder: builds share one lock and one saved
    # backend setting, so two labs built from the same folder collide.
    robocopy "$Project\terraform" "$Home1\terraform" /MIR /XD .terraform bastion guard /XF *.tfstate* /NFL /NDL /NJH /NJS | Out-Null
    if ($LASTEXITCODE -ge 8) { throw 'Could not copy the Terraform folder.' }
    $env:LAB_TERRAFORM_DIR     = "$Home1\terraform".Replace('\', '/')
    $env:LAB_WORKSPACE         = $Home1
    $env:LAB_ID                = $LabId
    $env:TF_VAR_lab_id         = $LabId
    $env:TF_VAR_region         = 'us-east-1'
    $env:TF_VAR_alert_email    = $AlertEmail
    $env:TF_VAR_budget_limit_usd = $BudgetLimitUsd
    $env:TF_VAR_guard_bucket   = "lab-guard-$($env:LAB_AWS_ACCOUNT_ID)-us-east-1"
    $env:TF_VAR_guard_budget_topic_arn = "arn:aws:sns:us-east-1:$($env:LAB_AWS_ACCOUNT_ID):lab-guard-budget"
    $env:BASE_DOMAIN           = $env:LAB_BASE_DOMAIN
    $env:PULL_SECRET_FILE      = "$Home1\pull-secret.txt".Replace('\', '/')
    Remove-Item Env:AWS_PROFILE -ErrorAction SilentlyContinue
    if ($DestroyAfter) { $env:TF_VAR_destroy_after = $DestroyAfter }
    if (-not $env:TF_VAR_destroy_after) { throw 'Pass -DestroyAfter YYYY-MM-DD (the date after which the guard destroys the lab).' }
}

switch ($Action) {
    'Build' {
        Require-AwsKeys
        Set-LabEnvironment
        lab up --yes
        if ($LASTEXITCODE -ne 0) { throw "lab up failed for $LabId. Run -Action Down before trying again." }
        lab keep $KeepHours
        Write-Host "$LabId is up. Next: -Action Deliver -BastionHost <ip>"
    }
    'Deliver' {
        if (-not $BastionHost) { throw 'Pass -BastionHost <public ip from terraform output>.' }
        if (-not (Test-Path "$Home1\.lab\kubeconfig")) { throw "No kubeconfig for $LabId. Build it first." }
        $dest = "$LabId@$BastionHost"

        # 1. The lab tool itself, without build files, tests or caches.
        $tgz = Join-Path $env:TEMP "lab-tool-$LabId.tgz"
        # The generators folder holds the module order that 'lab modules' and 'lab start' read.
        tar -czf $tgz --exclude=build --exclude=tests --exclude=__pycache__ --exclude='*.egg-info' -C $Project lab generators
        scp @SshOpts $tgz "${dest}:lab-tool.tgz"
        ssh @SshOpts $dest 'rm -rf ~/lab-tool && mkdir ~/lab-tool && tar -xzf ~/lab-tool.tgz -C ~/lab-tool && rm ~/lab-tool.tgz && python3.11 -m pip install --user -e ~/lab-tool/lab && grep -q ".local/bin" ~/.bashrc || echo "export PATH=\$HOME/.local/bin:\$PATH" >> ~/.bashrc'

        # 2. This learner's lab connection details (never your AWS sign-in).
        ssh @SshOpts $dest 'mkdir -p ~/lab-workspace/.lab && chmod 700 ~/lab-workspace ~/lab-workspace/.lab'
        foreach ($f in 'kubeconfig', 'lab.env', 'ingress-ca.crt', 'ca-bundle.crt', 'modules.json') {
            $p = "$Home1\.lab\$f"
            if (Test-Path $p) { scp @SshOpts $p "${dest}:lab-workspace/.lab/$f" }
        }
        ssh @SshOpts $dest 'chmod 600 ~/lab-workspace/.lab/kubeconfig ~/lab-workspace/.lab/lab.env'

        # 3. Build the tools container once, so the learner does not wait for it.
        ssh @SshOpts $dest '~/.local/bin/lab build-image'
        Write-Host "Handed over. The learner signs in with: ssh -i <their key> $dest   then runs: lab shell"
    }
    'Down' {
        Require-AwsKeys
        Set-LabEnvironment
        lab down --yes
    }
}

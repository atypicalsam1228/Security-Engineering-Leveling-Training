# Build the lab tools image on Windows (PowerShell). Does not push anywhere.
# Usage: .\build.ps1 [-Image lab-tools:latest]   Env: LAB_ENGINE=podman|docker, LAB_IMAGE
param([string]$Image = $(if ($env:LAB_IMAGE) { $env:LAB_IMAGE } else { "lab-tools:latest" }))
$ErrorActionPreference = "Stop"
$engine = $env:LAB_ENGINE
if (-not $engine) {
  if (Get-Command podman -ErrorAction SilentlyContinue) { $engine = "podman" }
  elseif (Get-Command docker -ErrorAction SilentlyContinue) { $engine = "docker" }
  else { Write-Error "Install podman or docker, then try again."; exit 2 }
}
Write-Host "Building $Image with $engine (this downloads about 400 MB of tools)"
& $engine build -t $Image -f (Join-Path $PSScriptRoot "Dockerfile") $PSScriptRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Built $Image. Check it with: $engine run --rm $Image bash -c 'oc version --client'"

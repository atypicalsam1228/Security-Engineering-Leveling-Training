#!/usr/bin/env bash
# Build the lab tools image for this computer's CPU (Mac M-series builds arm64,
# Intel Mac / Windows / most Linux build amd64). Does not push anywhere.
# Usage: ./build.sh [image-name]      Env: LAB_ENGINE=podman|docker, LAB_IMAGE
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
image="${1:-${LAB_IMAGE:-lab-tools:latest}}"
engine="${LAB_ENGINE:-}"
if [ -z "$engine" ]; then
  if command -v podman >/dev/null 2>&1; then engine=podman
  elif command -v docker >/dev/null 2>&1; then engine=docker
  else echo "ERROR: install podman or docker, then try again." >&2; exit 2; fi
fi
echo "Building $image with $engine (this downloads about 400 MB of tools)"
"$engine" build -t "$image" -f "$here/Dockerfile" "$here"
echo "Built $image. Check it with: $engine run --rm $image bash -c 'oc version --client'"

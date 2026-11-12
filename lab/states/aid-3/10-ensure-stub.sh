#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Deploys the stub model service (one copy of the code, kept in aid-2/stub/).
set -euo pipefail
bash "$(dirname "$0")/../aid-2/10-ensure-stub.sh"

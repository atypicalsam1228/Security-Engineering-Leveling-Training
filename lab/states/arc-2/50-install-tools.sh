#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Copies the supplied script to $HOME/arc and checks it runs under the image's python3.
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
mkdir -p "$HOME/arc"
cp "$(dirname "$0")/trace_stack.py" "$HOME/arc/trace_stack.py"
python3 "$HOME/arc/trace_stack.py" --help >/dev/null || die "trace_stack.py does not run under python3"
say "trace_stack.py is in $HOME/arc"

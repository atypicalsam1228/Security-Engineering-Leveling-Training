#!/usr/bin/env bash
# NOT YET RUN ON A LIVE CLUSTER. Idempotent: Gitea repository ai-tools under GITEA_USER with
#   main              - README, ailog.py (the Loki logging and query helper), seed_fixture.py (known sign-in events) and scope.py (the supplied scope check for Step 5), protected: merging needs a successful commit status "ai-script-review"
#   bad-summarizer    - a deliberately bad summarize.py (hardcoded token, no validation, no logging) for the negative test
set -euo pipefail
. "$(dirname "$0")/../_common/lib.sh"
require_env GITEA_URL GITEA_USER GITEA_TOKEN
gitea_ensure_repo ai-tools
gitea_put_file ai-tools main README.md "Add readme" "# ai-tools
Scripts that call the stub model service. Changes reach main only through a pull request that passed ai-script-review."

# ailog.py and seed_fixture.py are supplied (single copies in this folder; the AID-4 kit reuses ailog.py).
# AID-3 Step 3 shows ailog.py for reading; Step 5 runs seed_fixture.py and shows scope.py for reading. The learner writes tests/test_boolean.py (Step 2), pastes summarize.py and writes check_query.py.
here="$(dirname "$0")"
gitea_put_file ai-tools main ailog.py "Add logging helper" "$(cat "$here/ailog.py")"
gitea_put_file ai-tools main seed_fixture.py "Add known sign-in events for the query check" "$(cat "$here/seed_fixture.py")"

gitea_put_file ai-tools main scope.py "Add query scope check" "$(cat "$here/scope.py")"

gitea_ensure_branch ai-tools bad-summarizer main
BAD='import json
TOKEN = "sk-lab-0123456789abcdef"


def main():
    raw = ask("summary-prose")
    return json.loads(raw)'
gitea_put_file ai-tools bad-summarizer summarize.py "Add summarizer without checks" "$BAD"
gitea_put_file ai-tools bad-summarizer tests/test_empty.py "Add placeholder test" 'import unittest


class Placeholder(unittest.TestCase):
    def test_nothing(self):
        self.assertTrue(True)'

gitea_call GET "/repos/$GITEA_USER/ai-tools/branch_protections/main"
if [ "$GITEA_CODE" != 200 ]; then
  gitea_call POST "/repos/$GITEA_USER/ai-tools/branch_protections" \
    '{"branch_name":"main","rule_name":"main","enable_push":false,"enable_status_check":true,"status_check_contexts":["ai-script-review"],"required_approvals":0}'
  [ "$GITEA_CODE" = 201 ] || die "could not protect main in ai-tools (HTTP $GITEA_CODE)"
fi
say "ai-tools: main protected, branch bad-summarizer ready"

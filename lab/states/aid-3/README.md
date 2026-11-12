# AID-3 start state: AI-Assisted Automation Under Review

Applied by `lab start` / `lab reset` in file-name order. `.sh` files run with bash and must be idempotent.

Implemented: the files listed below.
- 10-ensure-stub.sh calls ../aid-2/10-ensure-stub.sh. The stub model service lives in aid-2/stub/ (one copy).
- 20-pipelines-and-gate.sh installs the pipelines operator if needed, creates project build, the gitea-clone secret,
  the config map ai-review-gate (from review_gate.py) and the Pipeline ai-script-review.
- 30-gitea-ai-tools-repo.sh creates repo ai-tools with ailog.py (the supplied Loki helper: log_event, push, query) and seed_fixture.py (eight known sign-in events for Step 5) and scope.py (the supplied query scope check for Step 5) on main, protects main with required status context ai-script-review,
  and adds branch bad-summarizer (a summarizer that fails the gate). ailog.py and seed_fixture.py are files in this folder; the AID-4 kit reuses ailog.py.
- The stub serves logql-good, logql-wrongfield and logql-wide (Step 5 drafts). check_query.py is written by the learner and is not part of the start state.
- 40-reference-answer.sh stores answers/test_boolean_count.txt in the config map aid3-reference (project build): the reference for the test the learner writes in Step 2 and for the flaw in the drafted shape.py (isinstance accepts true as a count). Opened only after trying.
- review_gate.py is the review gate: compiles, secret scan, banned calls, required log and parse calls, at least
  4 negative tests, runs unittest. Tested locally with python3.

Still needed: see TODO.md. Nothing here has run on a live cluster.

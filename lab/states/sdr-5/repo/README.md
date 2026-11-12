# detections

Detections as code. One file per detection in rules/, recorded sample events in samples/, the test and deploy
scripts in ci/. A change is merged only after its tests pass; the pipeline then publishes the rules to Grafana.

rules/NAME.json   uid, title, expr (LogQL), op, threshold, severity, control, tests
samples/NAME.jsonl   one recorded event per line: case, offset_s, labels, line
ci/               helpers (lokilib.py, replay.py, detlib.py, gf.py, mm.py); ci/task.yaml (the Tekton Task) is also supplied; you add run_tests.py, deploy.py, pipeline.yaml and measure.py

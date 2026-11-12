# ARC-3 start state: Choose an Admission Mode

Implemented: 05-preflight.sh, 10-namespace.yaml (arc-measure), 50-install-kit.sh (copies kit/ to $HOME/arc: four case pods, audit and enforce
versions of one Kyverno ClusterPolicy arc-baseline, load.yaml, set_mode.sh, snapshot.py, compare.py, review_gate.py, bad_measure.py).
The learner writes measure.py (not supplied). review_gate.py and the Python helpers were tested offline (gate pass and fail, memory/report/event counting).
Scripts have not been run on a live cluster.

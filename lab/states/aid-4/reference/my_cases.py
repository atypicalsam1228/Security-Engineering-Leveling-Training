MY_CASES = [
    ("oc get replicasets -n demo", True),
    ("oc get replicasets -n demo -o yaml", False),
]

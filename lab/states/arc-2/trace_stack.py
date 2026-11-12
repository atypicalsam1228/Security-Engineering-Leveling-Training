#!/usr/bin/env python3
"""Join live cluster facts into one JSON map: what each part does and which control it supports.

Reads only (oc get). Changes nothing. Exit codes:
  0  map built, nothing needs a person
  1  map built, but the "gaps" list has items a person must look at
  2  could not read the cluster; the map would be a guess, so none is printed
"""
import argparse
import json
import subprocess
import sys

TIER_NOTES = {
    "web": "Front end. Takes requests and calls the api.",
    "api": "Application logic. Called by the web part, calls the db.",
    "db": "Data store. Should be reachable only by the api.",
}
ENFORCED_TEXT = "Refuses a request that breaks the rule."
LOGGED_TEXT = "Allows the request and records a violation. Nothing is refused."


class Stop(Exception):
    """The cluster could not be read. Stop and ask; do not guess."""


def oc_json(args):
    try:
        done = subprocess.run(["oc", *args, "-o", "json"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as err:
        raise Stop("could not run oc: %s" % err)
    if done.returncode != 0:
        raise Stop("oc %s failed: %s" % (" ".join(args), done.stderr.strip() or "no message"))
    return json.loads(done.stdout)


def fetch(namespace):
    oc_json(["get", "namespace", namespace])
    return {
        "deployments": oc_json(["get", "deployments", "-n", namespace])["items"],
        "policies": oc_json(["get", "networkpolicies", "-n", namespace])["items"],
        "admission": oc_json(["get", "clusterpolicies.kyverno.io"])["items"],
    }


def pod_labels(deployment):
    return deployment["spec"]["template"]["metadata"].get("labels", {})


def selects(selector, labels):
    wanted = (selector or {}).get("matchLabels", {})
    return all(labels.get(key) == value for key, value in wanted.items())


def component(deployment):
    labels = pod_labels(deployment)
    tier = labels.get("tier", "")
    image = deployment["spec"]["template"]["spec"]["containers"][0]["image"]
    return {
        "name": deployment["metadata"]["name"],
        "image": image,
        "labels": labels,
        "does": TIER_NOTES.get(tier, "UNMAPPED"),
        "supports": ["CM-8"],
    }


def flows_from(policy, parts):
    out = []
    for rule in policy["spec"].get("ingress", []):
        ports = [p.get("port", "any") for p in rule.get("ports", [])] or ["any"]
        sources = rule.get("from", [])
        names = []
        for src in sources:
            if "podSelector" not in src:
                names.append("(selector outside the pod labels)")
                continue
            names += [c["name"] for c in parts if selects(src["podSelector"], c["labels"])]
        names = names or ["(anyone)"]
        for target in (c["name"] for c in parts if selects(policy["spec"].get("podSelector"), c["labels"])):
            out += [{"from": s, "to": target, "port": p, "allowed_by": policy["metadata"]["name"]} for s in names for p in ports]
    return out


def mode_of(policy):
    actions = {r.get("validate", {}).get("failureAction") or policy["spec"].get("validationFailureAction", "Audit") for r in policy["spec"]["rules"]}
    return actions.pop() if len(actions) == 1 else "Mixed"


def in_scope(policy, namespace):
    spaces = []
    for rule in policy["spec"]["rules"]:
        for block in rule.get("match", {}).get("any", []):
            spaces += block.get("resources", {}).get("namespaces", [])
    return not spaces or namespace in spaces


def admission_entry(policy):
    mode = mode_of(policy)
    return {
        "policy": policy["metadata"]["name"],
        "mode": mode,
        "rules": [r["name"] for r in policy["spec"]["rules"]],
        "effect": ENFORCED_TEXT if mode == "Enforce" else LOGGED_TEXT,
        "supports": ["CM-6"],
    }


def claims_for(flows, admission, namespace):
    out = []
    sources = {f["from"] for f in flows}
    leaves = [f for f in flows if f["to"] not in sources]
    if leaves:
        target = leaves[0]["to"]
        allowed = sorted({f["from"] for f in flows if f["to"] == target})
        text = "%s accepts connections only from %s." % (target, " and ".join(allowed))
        out.append({"id": "C1", "kind": "talks-to", "text": text})
    for kind, mode, number, text in (
        ("enforced", "Enforce", "C2", "A request that breaks %s is refused in " + namespace + "."),
        ("logged-only", "Audit", "C3", "A request that breaks %s is allowed, and a violation is recorded."),
    ):
        # Claims are about this module's own policies (arc-*), not other modules' policies that also match arc-lab.
        modal = [a for a in admission if a["mode"] == mode]
        match = next((a for a in modal if a["policy"].startswith("arc-")), None)
        if match:
            out.append({"id": number, "kind": kind, "text": text % match["policy"]})
    return out


def find_gaps(parts, policies, flows):
    gaps = []
    guarded = {t for p in policies if "Ingress" in p["spec"].get("policyTypes", []) for t in (c["name"] for c in parts if selects(p["spec"].get("podSelector"), c["labels"]))}
    for c in parts:
        if c["does"] == "UNMAPPED":
            gaps.append({"type": "unmapped", "name": c["name"], "detail": "no known tier label; owner and purpose unknown"})
        if c["name"] not in guarded:
            gaps.append({"type": "open-ingress", "name": c["name"], "detail": "no network policy limits who can reach it"})
        if c["image"].endswith(":latest") or ":" not in c["image"].split("/")[-1]:
            gaps.append({"type": "floating-image", "name": c["name"], "detail": "image tag does not name one version"})
    return gaps


def build_map(raw, namespace):
    parts = [component(d) for d in raw["deployments"]]
    flows = [f for p in raw["policies"] for f in flows_from(p, parts)]
    admission = [admission_entry(p) for p in raw["admission"] if in_scope(p, namespace)]
    gaps = find_gaps(parts, raw["policies"], flows)
    mechanisms = [{"kind": "NetworkPolicy", "name": p["metadata"]["name"], "supports": ["SC-7"]} for p in raw["policies"]]
    return {
        "namespace": namespace,
        "components": parts,
        "mechanisms": mechanisms,
        "flows": flows,
        "admission": admission,
        "gaps": gaps,
        "claims": claims_for(flows, admission, namespace),
        "summary": {"components": len(parts), "flows": len(flows), "admission": len(admission), "gaps": len(gaps)},
    }


def main():
    parser = argparse.ArgumentParser(description="Map the security parts of one namespace as JSON.")
    parser.add_argument("--namespace", default="arc-lab")
    args = parser.parse_args()
    try:
        result = build_map(fetch(args.namespace), args.namespace)
    except Stop as err:
        print("STOP: %s\nNothing was printed because a partial map would hide parts. Copy this message and ask your AI assistant before going on." % err, file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    print("components=%(components)d flows=%(flows)d admission=%(admission)d gaps=%(gaps)d" % result["summary"], file=sys.stderr)
    return 1 if result["gaps"] else 0


if __name__ == "__main__":
    sys.exit(main())

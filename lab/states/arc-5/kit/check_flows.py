#!/usr/bin/env python3
"""Usage: check_flows.py flows.yaml. Fails (exit 1) when the flow list is not acceptable as the source of truth."""
import re
import sys

import yaml

NAME = re.compile(r"^[a-z][a-z0-9-]{0,30}$")


def is_name(value):
    return isinstance(value, str) and bool(NAME.match(value))


def problems(data):
    if not isinstance(data, dict) or set(data) != {"namespace", "flows"}:
        return ["the top level must have exactly the keys: namespace, flows"]
    out = [] if is_name(data["namespace"]) else ["namespace must be a lowercase name"]
    flows = data["flows"]
    if not isinstance(flows, list) or not flows:
        return out + ["flows must be a list with at least one entry"]
    seen = set()
    for number, flow in enumerate(flows, 1):
        if not isinstance(flow, dict) or set(flow) != {"from", "to", "port"}:
            out.append("flow %d must have exactly the keys: from, to, port" % number)
            continue
        if not (is_name(flow["from"]) and is_name(flow["to"])):
            out.append("flow %d: from and to must be lowercase names" % number)
        elif flow["from"] == flow["to"]:
            out.append("flow %d: from and to are the same component" % number)
        port = flow["port"]
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            out.append("flow %d: port must be a whole number from 1 to 65535" % number)
        key = (flow["from"], flow["to"], port)
        if key in seen:
            out.append("flow %d repeats an earlier flow" % number)
        seen.add(key)
    return out


def main():
    try:
        data = yaml.safe_load(open(sys.argv[1]))
    except (OSError, yaml.YAMLError) as err:
        print("FAIL: cannot read the file: %s" % str(err).splitlines()[0])
        return 1
    found = problems(data)
    for item in found:
        print("FAIL: " + item)
    if found:
        return 1
    parts = {f[k] for f in data["flows"] for k in ("from", "to")}
    print("flows file OK: %d flows, %d components" % (len(data["flows"]), len(parts)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

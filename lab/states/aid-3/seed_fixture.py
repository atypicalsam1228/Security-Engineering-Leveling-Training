import json
import os
import sys

from ailog import push

EVENTS = [
    {"user": "alice", "event": "login_failed", "src": "10.0.0.5"},
    {"user": "alice", "event": "login_failed", "src": "10.0.0.5"},
    {"user": "alice", "event": "login_ok", "src": "10.0.0.5"},
    {"user": "alice", "event": "login_failed", "src": "10.0.0.9"},
    {"user": "bob", "event": "login_ok", "src": "10.0.0.7"},
    {"user": "bob", "event": "login_failed", "src": "10.0.0.7"},
    {"user": "carol", "event": "login_ok", "src": "10.0.0.8"},
    {"user": "carol", "event": "login_ok", "src": "10.0.0.8"},
]


def main():
    if os.path.exists("fixture.json"):
        print("fixture.json exists: the events were already pushed. Delete it only if that push is over an hour old.")
        return 1
    for event in EVENTS:
        push({"app": "ai-fixture"}, json.dumps(event))
    with open("fixture.json", "w", encoding="utf-8") as handle:
        json.dump(EVENTS, handle)
    print("pushed", len(EVENTS), "events to app=ai-fixture")
    return 0


if __name__ == "__main__":
    sys.exit(main())

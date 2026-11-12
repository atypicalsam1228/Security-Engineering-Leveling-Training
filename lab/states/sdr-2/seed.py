"""Push the SDR-2 exercise records to Loki and post the four alert messages. Usage: python3 seed.py ANCHOR_EPOCH_SECONDS

Every record carries seed_run=ANCHOR, so triage.py pins to this seeding and earlier copies that Loki still holds
(from a previous lab start or lab reset) are ignored. Earlier copies are also asked to be deleted.
"""
import json
import os
import sys
import time
import urllib.request

import lokilib as loki
from lokilib import NS
from events_sdr2 import ALERTS, SEED, build



def post_alerts(anchor_s, webhook):
    texts = {
        "A-101": "namespace=demo a role binding was created",
        "A-102": "namespace=keycloak sign-in failures above the limit",
        "A-103": "namespace=demo pod demo-app shell opened",
        "A-104": "namespace=demo pod demo-batch shell opened",
    }
    for alert_id, (kind, offset) in sorted(ALERTS.items()):
        when = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(anchor_s + offset * 60))
        text = "[FIRING:1] %s %s %s raised=%s" % (kind, alert_id, texts[alert_id], when)
        req = urllib.request.Request(webhook, data=json.dumps({"text": text}).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=30).read()


def main():
    anchor_s = int(sys.argv[1])
    loki.push(loki.tag_run(build(anchor_s * NS), anchor_s))
    print("  pushed exercise records to Loki (seed_run=%d)" % anchor_s)
    accepted, status = loki.purge_older_seeds(SEED, anchor_s)
    print("  asked Loki to delete earlier copies: %s (HTTP %s)" % ("accepted" if accepted else "not accepted, searches still pin to seed_run", status))
    if os.environ.get("SDR_NO_POST") != "1":
        post_alerts(anchor_s, os.environ["MM_WEBHOOK_URL"])
        print("  posted 4 alert messages to Mattermost")


main()

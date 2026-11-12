"""Push the SDR-4 exercise records to Loki. Usage: python3 seed.py ANCHOR_EPOCH_SECONDS [SUSPECT_POD_NAME]

The optional pod name replaces the example pod in the audit and Falco records, so that the timeline names a pod that exists.
Every record carries seed_run=ANCHOR, so searches can pin to this seeding and earlier copies that Loki still
holds (from a previous lab start or lab reset) are ignored. Earlier copies are also asked to be deleted.
"""
import sys

import events_sdr4
import lokilib as loki

anchor_s = int(sys.argv[1])
if len(sys.argv) > 2:
    events_sdr4.POD = sys.argv[2]
loki.push(loki.tag_run(events_sdr4.build(anchor_s * loki.NS), anchor_s))
print("  pushed exercise records to Loki (seed_run=%d)" % anchor_s)
accepted, status = loki.purge_older_seeds(events_sdr4.SEED, anchor_s)
print("  asked Loki to delete earlier copies: %s (HTTP %s)" % ("accepted" if accepted else "not accepted, searches still pin to seed_run", status))

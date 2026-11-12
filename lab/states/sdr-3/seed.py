"""Push the SDR-3 exercise records to Loki. Usage: python3 seed.py ANCHOR_EPOCH_SECONDS

Every record carries seed_run=ANCHOR, so searches can pin to this seeding and earlier copies that Loki still
holds (from a previous lab start or lab reset) are ignored. Earlier copies are also asked to be deleted.
"""
import sys

import events_sdr3
import lokilib as loki

anchor_s = int(sys.argv[1])
loki.push(loki.tag_run(events_sdr3.build(anchor_s * loki.NS), anchor_s))
print("  pushed exercise records to Loki (seed_run=%d)" % anchor_s)
accepted, status = loki.purge_older_seeds(events_sdr3.SEED, anchor_s)
print("  asked Loki to delete earlier copies: %s (HTTP %s)" % ("accepted" if accepted else "not accepted, searches still pin to seed_run", status))

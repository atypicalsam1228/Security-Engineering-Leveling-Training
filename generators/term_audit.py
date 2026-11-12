"""Lists technical words a module uses in its text that its terms table (and the common terms) do not cover.

Usage: python term_audit.py [ID ...]     Prints, per module, each uncovered word with a count.
A word counts as technical when it is in checks/allowlist.txt (jargon the spell checker does not know)
or in EXTRA below (ordinary English words that mean something specific here, such as token).
"""
from __future__ import annotations

import re
import sys
from collections import Counter

import common_terms
import order
import validate
from render import load_module

EXTRA = set("""token tokens secret secrets webhook webhooks credential credentials certificate certificates signature signatures
hash hashes checksum encryption cipher kubeconfig pipeline pipelines commit commits branch branches merge merged pull request requests
role roles binding bindings policy policies manifest manifests deployment deployments replica replicas selector selectors label labels
annotation annotations route routes ingress endpoint endpoints schema payload header headers query queries threshold baseline drift
registry registries tag tags digest digests artifact artifacts runner runners pod pods node nodes volume volumes mount mounts image images
container containers namespace namespaces cluster clusters operator operators controller controllers admission webhook scanner scanners
vulnerability vulnerabilities severity exploit exploits exposure inventory sbom provider providers plan state module modules variable
variables output outputs template templates playbook playbooks inventory idempotent""".split())


def vocabulary() -> set[str]:
    allow = {w.strip().lower() for w in (validate.CHECKS_DIR / "allowlist.txt").read_text(encoding="utf-8").split() if w.strip()}
    return {w for w in allow if len(w) > 2} | EXTRA


def text_of(m: dict) -> str:
    skip = {"terms", "glossary"}
    parts = [t for k, t in validate.prose({key: v for key, v in m.items() if key not in skip})]
    return "\n".join(parts)


def covered(m: dict) -> set[str]:
    words: set[str] = set()
    for term, _ in m["terms"]:
        low = term.lower()
        words.add(low)
        words.update(re.split(r"[^a-z0-9]+", low))
    for term in common_terms.COMMON:
        words.add(term)
    return {w for w in words if w}


def uncovered(m: dict, vocab: set[str]) -> Counter:
    have = covered(m)
    counts: Counter = Counter()
    for word in re.findall(r"[A-Za-z][A-Za-z0-9_-]+", text_of(m)):
        low = word.lower()
        stem = low[:-1] if low.endswith("s") and low[:-1] in vocab else low
        if (low in vocab or stem in vocab) and low not in have and stem not in have:
            counts[stem if stem in vocab else low] += 1
    return counts


def main(ids: list[str]) -> None:
    vocab = vocabulary()
    for mid in ids or order.TRACK:
        counts = uncovered(load_module(mid), vocab)
        print(f"== {mid}: {len(counts)} uncovered")
        print("   " + ", ".join(f"{w}({n})" for w, n in sorted(counts.items(), key=lambda kv: -kv[1])))


if __name__ == "__main__":
    main(sys.argv[1:])

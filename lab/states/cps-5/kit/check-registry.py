"""Checks the approved-registry rule in validate-images.yaml against six sample image names, before anything is applied.
Standard library only (runs on the lab shell's python3). It reads the file; it never talks to the cluster.
Kyverno image patterns: * matches any run of characters, ? one character, and | means or.
"""
import fnmatch
import os
import re
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "validate-images.yaml"
REGISTRY = os.environ.get("REGISTRY_HOST", "")
SAMPLES = [
    ("registry.access.redhat.com/ubi9/ubi-minimal:9.5", True),
    (REGISTRY + "/team/app:1.0", True),
    ("docker.io/library/busybox:1.36", False),
    ("quay.io/team/app:1.0", False),
    ("registry.access.redhat.com.example.org/app:1.0", False),
    ("busybox:1.36", False),
]


def rule_text(text):
    parts = re.split(r"(?m)^    - name: ", text)
    for part in parts:
        if part.startswith("approved-registry"):
            return part
    return ""


def admitted(pattern, image):
    return any(fnmatch.fnmatchcase(image, alt.strip()) for alt in pattern.split("|"))


def main():
    if not REGISTRY:
        sys.exit("REGISTRY_HOST is not set. Run this inside lab shell.")
    try:
        text = open(PATH, encoding="utf-8").read()
    except OSError as err:
        sys.exit("Cannot read " + PATH + ": " + str(err))
    rule = rule_text(text)
    if not rule:
        sys.exit("No rule named approved-registry in " + PATH)
    images = re.findall(r'(?m)^\s*- image: "(.*)"\s*$', rule)
    if not images:
        sys.exit("The approved-registry rule has no line like: - image: \"...\"")
    problems = []
    if len(images) != 2 or "=(initContainers):" not in rule:
        problems.append("The rule must check =(initContainers) and containers, each with its own image line (found %d image lines)." % len(images))
    pattern = images[-1].replace("${REGISTRY_HOST}", REGISTRY)
    right = 0
    for image, want in SAMPLES:
        got = admitted(pattern, image)
        ok = got == want
        right += ok
        print("%-6s %-8s %-3s %s" % ("allow" if want else "refuse", "admitted" if got else "refused", "ok" if ok else "BAD", image))
    print("samples handled as expected: %d of %d" % (right, len(SAMPLES)))
    for p in problems:
        print("Problem: " + p)
    if len(set(images)) > 1:
        print("Problem: the two image lines differ; use the same allow-list for both.")
    sys.exit(0 if right == len(SAMPLES) and not problems and len(set(images)) == 1 else 1)


main()

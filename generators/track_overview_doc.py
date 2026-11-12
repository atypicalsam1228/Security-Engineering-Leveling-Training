"""Builds ENGINEERING-TRACK.docx, the learner-facing overview of the track.

Usage: python track_overview_doc.py     Writes ENGINEERING-TRACK.docx and ENGINEERING-TRACK.md to the project root.
Layout follows the earlier "Training Protocol" documents: audience, goal, then one phase per
dimension with a "why this order" line and, for each module, a description, the steps you
will do and the tools and services used. Descriptions, step titles and tools are read from
the module files so they cannot drift.
"""

from __future__ import annotations

import re
from pathlib import Path

from doc_builder import DocBuilder
from order import TRACK
from render import load_module

ROOT = Path(__file__).resolve().parent.parent

AUDIENCE = "Someone with basic cybersecurity and IT knowledge who wants to do hands-on security engineering work."
GOAL = (
    "Learn to do security engineering work on a real system. You will collect compliance evidence, "
    "find and prioritize vulnerabilities, investigate alerts and write detections, harden and secure "
    "a workload, use AI tools and agents safely, and test and verify security designs. Every module "
    "is hands-on: you run real tools on your own OpenShift cluster in AWS, prove each change works "
    "with a test, and prove what fails when the control is removed. By the end you can automate the "
    "work, deliver it through an automated review, and design a pattern a whole team can inherit."
)

PHASES = [
    ("Foundation", ["ENG-0", "ENG-1"], "Why first: every later module uses the terminal, git, the oc command and the platform health check from ENG-0, and the picture of how a call travels from a name to a pod from ENG-1."),
    ("GRC Engineering", ["GRC-2", "GRC-3", "GRC-4", "GRC-5"], "Why this order: you run evidence collection by hand, automate it, put it in the delivery pipeline, then design continuous monitoring across controls."),
    ("Vulnerability Management", ["VM-2", "VM-3", "VM-4", "VM-5"], "Why this order: you scan and hand off findings, track fixes, prioritize by context, then gate delivery on risk."),
    ("Security Data and Incident Response", ["SDR-2", "SDR-3", "SDR-4", "SDR-5"], "Why this order: you triage an alert from a runbook, investigate and tune, build detections, then manage them as code."),
    ("Cloud and Platform Security", ["CPS-2", "CPS-3", "CPS-4", "CPS-5"], "Why this order: you apply a baseline, limit permissions, secure a whole workload, then build guardrails developers inherit."),
    ("AI Development", ["AID-2", "AID-3", "AID-4", "AID-5"], "Why this order: AID-2 is optional; you check AI-written scripts, put AI-assisted automation under review, build a constrained agent, then set the safe-adoption pattern. No model account or key is needed; a stand-in model gives scripted answers."),
    ("Architecture and Design", ["ARC-2", "ARC-3", "ARC-4", "ARC-5"], "Why this order: you trace the security stack, choose an admission mode, test two designs, then verify a reference architecture."),
    ("Infrastructure as Code", ["IAC-1", "IAC-2", "IAC-3"], "Why this order: you run a supplied baseline as code with Terraform and Ansible, then deliver your own change through a review gate, then choose between the two tools by evidence. This dimension has three modules, numbered in sequence."),
]
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def description(module: dict) -> str:
    """First two sentences of the module's requirement text."""
    sentences = SENTENCE_END.split(module["requirement"].strip())
    return " ".join(sentences[:2])


def build() -> None:
    b = DocBuilder()
    b.title("Engineering Leveling Training")
    b.para(f"Target Audience: {AUDIENCE}")
    b.para(f"Goal: {GOAL}")
    b.para("Each module has at most five steps. You run it in your lab shell on your own cluster. Start any module with `lab start <id>`, for example `lab start grc-3`.")

    b.h1("Suggested order")
    levels, current = [], []
    for mid in TRACK[2:]:
        if mid.startswith("GRC-") and current:
            levels.append(current)
            current = []
        current.append(mid)
    levels.append(current)
    b.numbered("Start with ENG-0, then ENG-1. Every other module assumes ENG-0 and its earlier modules in the same dimension. The cloud and platform security and the architecture modules also use what ENG-1 teaches about how traffic moves.")
    b.numbered("Then take one level across all seven dimensions, in this order: " + "; then ".join(", ".join(ids) for ids in levels) + ". This is the order the `lab modules` command lists.")
    b.numbered("Or take one dimension through its levels in order (infrastructure as code has three modules). Each level builds on the one before it in the same dimension and says what it assumes.")
    b._md()

    for index, (name, ids, why) in enumerate(PHASES):
        b.h1(f"Phase {index + 1}: {name}")
        b.para(why)
        for mid in ids:
            module = load_module(mid)
            b.h2(f"{mid} - {module['title']}")
            b.para(description(module))
            b.para("What you will do:")
            for step in module["steps"]:
                b.bullet(step["title"])
            b._md()
            b.para("Tools and services: " + ", ".join(module["tools"]))

    b.doc.save(ROOT / "ENGINEERING-TRACK.docx")
    markdown = list(b.md_lines)
    markdown += ["## Reference: controls and timed minutes", "",
                 "Timed work is hands-on plus verify. Reading is not timed.", "",
                 "| Module | Title | Controls | Minutes |", "| --- | --- | --- | --- |"]
    for mid in TRACK:
        module = load_module(mid)
        minutes = module["minutes"]["hands_on"] + module["minutes"]["verify"]
        markdown.append(f"| {mid} | {module['title']} | {', '.join(module['controls']) or 'none'} | {minutes} |")
    markdown.append("")
    (ROOT / "ENGINEERING-TRACK.md").write_text("\n".join(markdown), encoding="utf-8")
    print("wrote", ROOT / "ENGINEERING-TRACK.docx", "and .md", dict(b.counts))


if __name__ == "__main__":
    build()

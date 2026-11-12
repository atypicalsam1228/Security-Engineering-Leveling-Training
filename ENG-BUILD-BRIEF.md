# Engineering Track Build Brief

You are writing modules for the engineering leveling track. Read `BUILD-BRIEF.md` first: its schema, rules and checks apply to every module here. Then read `LAB-CONTRACT.md` and a finished module in this track. Prerequisites are ENG-0 and earlier modules of the same dimension only. This file adds what is specific to the levels.

## Who and what

Technical and engineering skills only. No documentation work: the learner writes scripts, queries, configs and checks, never reports or narratives. The lab platform (single-node OpenShift cluster, tools container, namespaces, tools and variables in `LAB-CONTRACT.md`) is described in the contract. Every module must run alone: its `lab.start` loads everything it needs, and anything only the lab build can install is listed in `lab_needs` and `TODO.md`.

The track has six dimensions, each taken at four levels. A module id is `DIMENSION-N`, where N is the level it targets (`-2` covers levels 1 and 2). Content file: `generators/content/<dimension>_<n>.py` (for example `grc_3.py`). Every module in the track is already listed in `generators/order.py` (`TRACK`); do not edit that file.

## What each level means in a module

| Level | The learner's role | Shape of the module |
|---|---|---|
| 2 (levels 1 and 2) | Runs existing tools and scripts with guidance, reads the output, knows when to stop and escalate | Steps run supplied assets and read results. Nothing is built from scratch. The negative test shows what a failure or a bad input looks like and what to do next. |
| 3 | Automates a small repeated task and delivers it through review | The learner writes a short script or config (at most about 30 lines per block) and passes it through an automated review gate (a check that fails when the work is not acceptable), then runs it. |
| 4 | Independently builds and integrates a working solution, weighing trade-offs with context | The learner connects two or more lab tools into one working flow, chooses between options using evidence from the cluster, and proves the result with a positive and a negative test. |
| 5 | Designs a pattern a whole team inherits and measures whether it works | The learner picks parameters and a design, builds it so other teams get it by default, and proves it with a measurement (for example time to detect, percent of workloads covered, number of manual steps removed). Trade-offs are stated in technical terms and tested. |

Each level builds on the previous one in the same dimension. Say what the previous level taught in `prereq`, but do not repeat it.

## Rules specific to this track

- Do not name or quote the leveling document these modules came from. Describe skills in plain words. The validator bans its name.
- Timed work stays at 60 to 75 minutes (hands-on plus verify), at most 5 steps.
- Where the learner writes code, give the finished code in the step (they type or paste it), explain it line by line, and make every code block pass the validator. Review gates are scripts or Tekton/Gitea checks that exist in the lab or that a step creates; they must really fail on bad input (the negative test proves it).
- Use only commands already available in the tools container (oc, kubectl, jq, curl, git, openssl, terraform, aws, python3, cosign, trivy, tkn, argocd, plus standard shell utilities already in `generators/checks/commands.txt`). Do NOT add commands to `checks/commands.txt`, `checks/allowlist.txt` or `lab/image/versions.txt`; if you truly need one, use a different approach, or list it in your final report.
- AWS calls from the lab shell are read-only unless the module's `lab_needs` says otherwise.
- Controls: choose 2 to 4 controls per module that the module really exercises, and quote them from `nist-sp-800-53r5-full.md`, and `fedramp-high-baseline.md` exactly as BUILD-BRIEF describes. Check the quote exists (the validator does). Control references go in the module text only for controls listed in `controls` or `mentions`.
- Where the lab needs something that does not exist yet (a sample workload, seeded log events, a stub service), put it in `lab/states/<id lower>/` as scripts and manifests following `lab/states/grc-2/`, write a `README.md` there listing what is implemented, and list anything not buildable offline under `lab_needs` and in `TODO.md`. Do not edit `LAB-CONTRACT.md`.
- Optional faults: add a "Break It and Watch" section (1 to 3 faults) only if the module has real operational failure modes worth practising. It is always optional. Most level 2 modules need none. The fault fields are read by `generators/render.py` and `generators/validate.py`; no module in the track uses them yet.
- Diagrams: one diagram per module with `per_step: True`, following the examples. LOOK at the rendered images in `modules/img/` before you finish: nothing overlapping, every node inside a boundary, labels readable.
- Put the module's own assumptions that you could not confirm live in its `draft` text. Nothing here has run on a live cluster.

## Shared files

If several people write modules at once, do not edit any file outside your own `generators/content/<your files>.py`, your own `lab/states/<your ids>/` folders and the images and documents the renderer produces for your ids. In particular do not edit `render.py`, `validate.py`, `module_diagrams.py`, `order.py`, the checks lists, the README files, `LAB-CONTRACT.md` or the terraform folder. If the validator or renderer blocks you for a reason that needs one of those files, say so in your report and work around it.

## Finishing

For each module: `cd "<project>/generators" && python validate.py <ID>` until 0 errors; review every warning. Then `python render.py <ID>`, and look at its images. Final report in under 250 words: files written, validator result per module, and a bullet list of unresolved items (organization-defined parameters, commands or fields you could not confirm, lab needs, anything you needed from a shared file).

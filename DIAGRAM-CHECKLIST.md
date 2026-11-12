# Diagram rollout checklist

Reference examples: `generators/content/grc_2.py` and `generators/content/arc_4.py` (the `diagrams` entry). Format spec: docstring of `generators/module_diagrams.py`.

## A. Per module (the drawing agent ticks these)
- [ ] Decide whether the module needs a diagram. If it is only reading or terminal basics, add none and say why in the report.
- [ ] One diagram, `per_step: True`, with a `step_notes` sentence for every step (capitalized, ends with a period).
- [ ] The finished picture shows the system as built by the last step. Each part has `s=N` equal to the step that creates it (parts that already exist have no `s`). Use `until` only where a flow is replaced.
- [ ] Every node is inside a zone. Boundaries match the module text (cluster, project, host, account). No node outside the dashed boundary.
- [ ] Every title, sub, zone label and edge label starts with a capital letter. Plain grammar. No raw tool jargon without a plain label.
- [ ] At most 12 nodes. Edges labeled with a verb. Flow numbers (`n`) only where order matters.
- [ ] Colors mean something: ok = healthy or allowed, bad = blocked or failing, warn = needs attention, neutral otherwise.
- [ ] Facts match the module's own steps, names and ports. Nothing drawn that the module does not build or explain.
- [ ] No real company or program names. ASCII only.
- [ ] `python validate.py <ID>` shows 0 errors, 0 warnings.
- [ ] `python render.py <ID>`, then LOOK at the final PNG and at least two step PNGs in `modules/img/`. Check: no overlap, no clipped text, layout identical between steps, nothing outside the boundary, readable at page width.

## B. After all modules (the lead does these)
- [ ] `python validate.py --all` clean.
- [ ] `python render.py --all` clean (close Word first).
- [ ] Spot-view one diagram from each batch.
- [ ] `/rmf-vault review` over every diagram's labels and claims (control IDs, parameters, ownership). Fix DRIFT, flag UNVERIFIED.
- [ ] Full module review (REVIEW-CHECKLIST.md sections A-E) of all 16 modules after the diagrams are in, including the Word rendering. Results go in `the review log for that module`.
- [ ] Update memory file and report open items.

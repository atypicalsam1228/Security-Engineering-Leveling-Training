# Learner-view rollout checklist (Engineering Leveling Training)

STATUS: ENG-0 and the GRC-2 pilot are approved. The other 23 modules are content-done and verified by script; the owner has not yet opened them. Note: accuracy_auto.py cannot read a .docx that is open in Word (it reports Package not found).

Rules for agents:
- Work one module at a time. Do not change ENG-0.
- Do ENG-0's sibling pilot first: GRC-2. Stop and let the owner open `modules/GRC-2-RunEvidence.docx` before doing the other 23.
- Never put a real organization name, an invented story, or a number you cannot trace into learner text (see ENG-BUILD-BRIEF.md).
- All text is plain ASCII. Keep sentences short; explain every technical word in plain words the first time it appears.
- Use the Edit tool for Python edits, not shell heredocs: a backslash inside a heredoc gets mangled.

## 1. What changed in ENG-0 (the model)

Reference file: `generators/content/eng_0.py`. Read it before starting; every item below is visible there.

| # | Change | Where it lives | Applies to |
|---|---|---|---|
| 1 | Builder notes are not shown to learners. The DRAFT paragraph stays in the content file (`draft`) and in `lab/states/<id>/TODO.md`. | module flag `"hide_draft": True`; `render.py` `_header` | every module |
| 2 | Terms get a hover pop-up. First use of each term in the body shows its meaning in Word when hovered. Terms table gets bookmarks. | module flag `"hover": True`; `DocBuilder.terms_table`, `_link`, `_hover_link` | every module |
| 3 | The tool table gets a fourth column, "Why this tool". | module flag `"tool_why": True`; `_WHY` dict in `generators/tool_links.py` | every module |
| 4 | Every command table gets a third column, "Why you run it". | third item in every `lines` row | every code block in every step |
| 5 | The diagram section explains why the setup is built this way, names each box clearly, and lists the boxes as hover names. | diagram keys `why_built`, `legend`, optional `setup`; `module_diagrams.py` `render_diagrams`; `DocBuilder.hover_names` | every module that has a diagram |
| 6 | Step and diagram sentences say where things go ("sends your change back to that same repository on Gitea, on the branch named main"), never just "back" or "it". | text in `step_notes`, `reading`, step text | every module |
| 7 | Builder file fixes (done once): paragraph shading element order, zoom percent. | `generators/doc_builder.py` | done |

## 2. Per-module work (do all of these for each module)

### 2.1 Flags
Add to the MODULE dict, next to `tools`:
```python
"tool_why": True,
"hide_draft": True,
"hover": True,
```

### 2.2 Terms (hover)
1. Read the whole module text. List every word a new learner might not know: tools, objects, file formats, concepts (examples from ENG-0: workload, cluster, container, YAML, Gitea, variable, namespace, pod).
2. Add each to `terms` as `("Term", "Plain meaning.")`. Meaning at most 250 characters (Word's pop-up limit), one or two plain sentences, no jargon that is not itself a term.
3. Also define the word inline in the body at its first use, in brackets or a short clause: "workloads (programs the cluster runs, such as demo-app)".
4. Keep terms unique per module. Plurals match automatically ("pods" matches "Pod"). Do not add very common words (for example "file").
5. Terms in `glossary` stay; `terms` is the hover set.

### 2.3 Why this tool
In `generators/tool_links.py`, `_WHY` is keyed by the tool name used in `TOOLS` (for example `"oc"`, `"Gitea"`). Add one entry for every tool any module lists that is not yet there. Each entry says why the lab uses this tool and not another way to do the same job, in one to three sentences. A tool with no entry shows an empty cell: do not leave any.

Example:
```python
"oc": "It is the one command that talks to the cluster, so every module uses it to ask what is true and to make changes. ... Unlike clicking in the web console, a command can be pasted, repeated and checked by a test.",
```

### 2.4 Why you run it (command tables)
Every row of every step's `lines` list becomes a three-item tuple: `(part, what it does, why you run it)`. The third item is the purpose at that point in the exercise, not a restatement of the second. All rows in a table must have three items (the renderer only adds the column when every row does).

Example:
```python
("oc logs -n kyverno \"$pod\" --tail=3", "Prints the last three lines of that pod. This one is busy, so you see text.",
 "Compare with the quiet demo pod: a busy pod shows text, so you learn what normal looks like for each."),
```

### 2.5 Diagrams
For each diagram in `diagrams`:
1. Rename any box whose name does not say what it is. A tool and the server it talks to must not share a name (use "Git client" and "Gitea (the git server)", not "Git" and "Gitea"). Every node and zone title must start with a capital letter (the validator checks this).
2. `legend`: a list of `("Box title", "What it is, in one or two plain sentences.")` for every node. The title must equal the node `title` exactly. Zones may be added. At most 250 characters each.
3. `why_built`: four to six sentences answering "why is the whole thing set up this way?": where the learner works, where things run, what talks to what and why, why those parts live where they do. For a module after ENG-0, say what this module adds to the lab layout the foundation module showed, and why it belongs there. Do not describe how the picture is drawn.
4. `setup` (optional, recommended for any module that adds a new part): rows of `(Part, Where it runs, Why it is built this way)`.
5. Re-read `step_notes` and `reading`: every arrow, push, copy or send names its destination.

### 2.6 Things that must NOT be added
- No picture overlays, floating shapes or thumbnails over a diagram for hover. They were tried in Word desktop and do not show pop-ups. Only text hover works.
- Do not list the legend as bullets in the Word file; the hoverable names line replaces it (the `.md` keeps a list automatically).

## 3. Verify (every module)

Close the module's `.docx` in Word first; Word locks the file and rendering fails with "Permission denied". If it is open, render to a scratch folder instead (`render.OUT_DIR = Path(scratch)`) and tell the owner.

Before regenerating a module's `.docx`, read its comments (regenerating erases them):
```python
import zipfile, re
z = zipfile.ZipFile("modules/<file>.docx")
print("word/comments.xml" in z.namelist())
```
If there are comments, report them to the owner and do not regenerate until told.

Then, per module `<ID>`:
- [ ] `python generators/render.py <ID>`
- [ ] `python generators/validate.py <ID>` prints `0 errors, 0 warnings`
- [ ] `python generators/accuracy_auto.py` shows no failure for this module (it cannot read a file that is open in Word)
- [ ] The Word file passes the docx validator: `python "<docx-skill>/scripts/office/validate.py" <copy of the docx>` prints `All validations PASSED!` (copy the file to the scratch folder first)
- [ ] Hover links resolve and are short enough:
```python
import zipfile, re
x = zipfile.ZipFile("<docx>").read("word/document.xml").decode()
links = re.findall(r'<w:hyperlink w:anchor="([^"]+)" w:tooltip="([^"]*)"', x)
names = set(re.findall(r'w:name="([^"]+)"', x))
assert all(a in names for a, _ in links), "dangling link"
assert all(len(t) <= 250 for _, t in links), "tooltip too long"
```
- [ ] No `What each box is` text remains in the `.docx`; the `.md` still lists the box meanings
- [ ] The tool table has four columns; every "Why this tool" cell is non-empty
- [ ] Every command table has three columns
- [ ] The DRAFT paragraph is absent from the `.docx` and still present in the content file
- [ ] The owner opens one Word file per batch and hovers over a dotted word and over a box name

## 4. Module tracker

Tick a box only when every item in section 3 passes for that module.

| Module | Content done | Verified | Owner opened |
|---|---|---|---|
| ENG-0 | [x] | [x] | [x] |
| GRC-2 (pilot) | [x] | [x] | [x] |
| ENG-1 (new, pilot) | [x] | [x] | [ ] |
| GRC-3 | [x] | [x] | [ ] |
| GRC-4 | [x] | [x] | [ ] |
| GRC-5 | [x] | [x] | [ ] |
| VM-2 | [x] | [x] | [ ] |
| VM-3 | [x] | [x] | [ ] |
| VM-4 | [x] | [x] | [ ] |
| VM-5 | [x] | [x] | [ ] |
| SDR-2 | [x] | [x] | [ ] |
| SDR-3 | [x] | [x] | [ ] |
| SDR-4 | [x] | [x] | [ ] |
| SDR-5 | [x] | [x] | [ ] |
| CPS-2 | [x] | [x] | [ ] |
| CPS-3 | [x] | [x] | [ ] |
| CPS-4 | [x] | [x] | [ ] |
| CPS-5 | [x] | [x] | [ ] |
| AID-2 | [x] | [x] | [ ] |
| AID-3 | [x] | [x] | [ ] |
| AID-4 | [x] | [x] | [ ] |
| AID-5 | [x] | [x] | [ ] |
| ARC-2 | [x] | [x] | [ ] |
| ARC-3 | [x] | [x] | [ ] |
| ARC-4 | [x] | [x] | [ ] |
| ARC-5 | [x] | [x] | [ ] |

## 5. After all modules

- [ ] `python generators/validate.py --all` (takes two or more minutes; run it in the background) shows 0 errors and 0 warnings
- [ ] `python generators/accuracy_auto.py` passes
- [ ] `python generators/track_overview_doc.py` rebuilds `ENGINEERING-TRACK.docx`
- [ ] Nothing is committed until the owner says so

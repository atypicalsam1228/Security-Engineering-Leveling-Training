"""AI-2: Check a model file before you use it (SI-7, CM-14, SR-4)."""

NIST = "nist-sp-800-53r5-full.md"
WORK = "cd /workspace/ai-2\n"
SIGN = (
    "COSIGN_PASSWORD=\"$(cat signing.pass)\" cosign sign-blob --yes --key cosign.key --use-signing-config=false --tlog-upload=false "
    "--bundle model/manifest.bundle.json model/manifest.json > /dev/null\n"
)
VERIFY = "cosign verify-blob --key cosign.pub --bundle {d}/manifest.bundle.json --insecure-ignore-tlog=true {d}/manifest.json"

MODULE = {
    "intent_at_end": True,
    "terms_at_end": True,
    "id": "AI-2",
    "slug": "ModelProvenance",
    "title": "Check a Model File Before You Use It",
    "draft": (
        "Written without a live cluster; no command in this module has been run. Unconfirmed: that the Cosign release in lab shell accepts the same sign-blob and verify-blob flags that GRC-4 uses with --bundle "
        "(GRC-4 confirmed them in a pipeline image, not in lab shell), that generate-key-pair with a COSIGN_PASSWORD value writes cosign.key and cosign.pub into the current folder without a prompt, "
        "and that python3 in lab shell is 3.9 or later (capture_output needs 3.7). The module needs no cluster resource. "
        "The model file is a random stand-in made by head -c on /dev/urandom, so the lab proves the checks and not a real model's origin. "
        "A bare key pair is not a certificate recognized and approved by an organization, which CM-14 names; see the intent for that control."
    ),
    "controls": ["SI-7", "CM-14", "SR-4"],
    "mentions": [],
    "unit_values_ok": ["4096 bytes", "12 characters"],
    "minutes": {"hands_on": 35, "verify": 15},
    "tools": ["Python (python3)", "Cosign (free, open source)", "openssl", "jq", "curl"],
    "tool_why": True,
    "hide_draft": True,
    "hover": True,
    "diagrams": [
        {
            "id": "provenance",
            "title": "The loader trusts a file only after two checks",
            "caption": "In the lab (test) setup, a hash record lists the model file, a signature covers the record, and the loader checks both before it uses the file. New parts are drawn with thick lines.",
            "per_step": True,
            "rankdir": "LR",
            "step_notes": {
                1: "A stand-in model file is made and a hash record lists its name and hash.",
                2: "A key pair signs the record, so a changed record no longer verifies.",
                3: "The loader checks the signature on the record and then the hash of the file, because the signature alone does not cover the file.",
            },
            "zones": [
                {"id": "ws", "icon": "brands/linux", "label": "Your lab shell (a container on your computer)", "kind": "boundary"},
                {"id": "folder", "label": "Folder /workspace/ai-2", "parent": "ws", "kind": "group"},
            ],
            "key": {"k8s/vol": "Model file", "brands/json": "Hash record", "k8s/secret": "Key pair and signature", "brands/python": "Python script"},
            "nodes": [
                {"id": "model", "icon": "k8s/vol", "title": "Model file", "sub": "Stand-in model weights", "zone": "folder", "s": 1},
                {"id": "rec", "icon": "brands/json", "title": "Hash record", "sub": "File name and hash, made with jq", "zone": "folder", "s": 1},
                {"id": "keys", "icon": "k8s/secret", "title": "Key pair", "sub": "Private key signs, public key verifies", "zone": "folder", "kind": "ok", "s": 2},
                {"id": "sig", "icon": "k8s/secret", "title": "Signature", "sub": "Cosign signature of the record", "zone": "folder", "kind": "ok", "s": 2},
                {"id": "loader", "icon": "brands/python", "title": "Loader", "sub": "Python script that decides whether to load", "zone": "folder", "kind": "warn", "s": 3},
            ],
            "edges": [
                {"a": "rec", "b": "model", "label": "Lists hash", "s": 1},
                {"a": "keys", "b": "sig", "label": "Signs record", "kind": "ok", "s": 2},
                {"a": "sig", "b": "rec", "label": "Covers", "s": 2},
                {"a": "loader", "b": "sig", "label": "Verifies", "kind": "ok", "s": 3},
                {"a": "loader", "b": "model", "label": "Checks hash", "kind": "ok", "s": 3},
            ],
            "reading": [
                "1. Model file: a stand-in for real model weights.",
                "2. Hash record: a file that lists the model file name and its hash.",
                "3. Key pair: a private key that signs and a public key that verifies.",
                "4. Signature: the Cosign signature of the hash record.",
                "5. Loader: a Python script that verifies the signature on the record and then checks the hash of the model file before it loads anything.",
            ],
        },
    ],
    "prereq": [
        "GRC-4 Evidence Signing (cosign sign-blob and verify-blob with a key pair, and what a signature does and does not cover)",
    ],
    "lab_needs": [],
    "lab": {
        "start": "lab start ai-2",
        "env": [],
    },
    "requirement": (
        "A model file (the saved numbers that make up a model) is software that the system will run, and it usually comes from somewhere else. "
        "A model file that was swapped, damaged or planted behaves differently from the one that was approved, and nothing about its size or name shows it. "
        "So the system records where each model file came from and what it should contain, checks a digital signature (a mark only the key holder can make) on that record, "
        "and checks the file itself against the record before it loads it. A file that fails any check is not loaded, whether it was damaged by accident or by tampering. "
        "This module builds a small loader that does those checks and shows each one refusing something."
    ),
    "objectives": [
        {"label": "Skill", "text": "Record a model file's source and hash, sign the record, and write a loader that refuses a file whose signature or hash does not match."},
        {"label": "Tools", "text": "`openssl` computes the hash; `jq` writes the record; `cosign` signs and verifies it; `python3` runs the loader."},
        {"label": "Security Function", "text": "Detects a model file that has been changed since it was approved, and detects a record that did not come from the key holder, then refuses to load either."},
        {"label": "NIST SI-7 Software, Firmware, and Information Integrity", "text": "The loader recomputes the file's hash and compares it with the signed record, and refuses to load on a mismatch."},
        {"label": "NIST CM-14 Signed Components", "text": "The loader refuses a record whose signature does not verify with the approved public key."},
        {"label": "NIST SR-4 Provenance", "text": "The signed record names the file, its source, its hash and when it was recorded."},
    ],
    "requirement_bullets": [
        "Purpose: show that a model file is software from outside, that its origin and contents are recorded, and that the system checks both before it uses the file.",
        "You make the record, sign it and run a loader. You write one piece yourself: the hash check that the first loader is missing.",
        "You test one load that must succeed and two that must be refused.",
    ],
    "mapping": [
        {
            "control": "SI-7 Software, Firmware, and Information Integrity",
            "plain": "Detect unauthorized changes to software and information, and act when one is found.",
            "source": "NIST",
            "tool": "`openssl`, which computes the hash, and the loader written in `python3`. Explained in section 2.1.",
            "covered": "Section 3, Step 1: record the file's hash. Section 3, Step 3: refuse a file whose hash differs. Section 4, Test 2: a changed file is refused.",
            "cite": [
                {"file": NIST, "quote": "Employ integrity verification tools to detect unauthorized changes to the following software, firmware, and information"},
                {"file": NIST, "quote": "Take the following actions when unauthorized changes to the software, firmware, and information are detected"},
            ],
        },
        {
            "control": "CM-14 Signed Components",
            "plain": "Do not install certain components unless they are digitally signed in a way the organization approves.",
            "source": "NIST",
            "tool": "`cosign`, which signs and verifies the record. Explained in section 2.2.",
            "covered": "Section 3, Step 2: sign the record and verify it with the public key. Section 3, Step 3: the loader refuses a record that does not verify. Section 4, Test 3: an edited record and a missing signature are both refused.",
            "cite": [
                {"file": NIST, "quote": "without verification that the component has been digitally signed using a certificate that is recognized and approved by the organization"},
            ],
        },
        {
            "control": "SR-4 Provenance",
            "plain": "Keep a record of where each component came from, and keep it valid.",
            "source": "NIST",
            "tool": "`jq`, which writes the record (manifest.json). Explained in section 2.3.",
            "covered": "Section 3, Step 1: write the record with the name, source, hash and time. Section 4, Test 1: the loader prints the recorded name only after the checks pass.",
            "cite": [
                {"file": NIST, "quote": "Document, monitor, and maintain valid provenance of the following systems, system components, and associated data"},
            ],
        },
    ],
    "intent": [
        {
            "control": "SI-7 Software, Firmware, and Information Integrity",
            "feared": "A model file is changed after it was approved, in storage or on the way, and the system loads it without noticing.",
            "scope": "The model file that the loader is asked to load. Files the loader never reads are outside this module.",
            "question": "How does the system know the file it is about to load is the one that was approved, and what does it do when it is not?",
            "evidence": "The recorded hash, the loader's comparison, and a refusal that stops the load.",
            "sufficient": "The loader recomputes the hash of the file itself, at load time, and compares it with the hash in the signed record. NIST leaves the list of software and information to check, and the actions to take on a change, to the organization. The lab checks the model file and the action is to refuse and exit with status 1.",
            "tieoff": "A refusal is printed and the exit status is 1, so a person or a schedule can see it. Reporting the refusal to the people who must act is left to the monitoring modules.",
            "tool": "`openssl dgst` (Step 1) computes the hash, and the check you write in Step 3 compares it in the loader.",
        },
        {
            "control": "CM-14 Signed Components",
            "feared": "The record that names the expected hash is itself replaced, so a swapped file comes with a matching record and passes the hash check.",
            "scope": "The record manifest.json that sits next to the model file.",
            "question": "Who vouched for this record, and does the loader check that before it trusts what the record says?",
            "evidence": "A signature on the record that verifies with the approved public key, and a refusal when it does not.",
            "sufficient": "The loader verifies the signature with the public key before it reads the record. NIST asks for a certificate recognized and approved by the organization, and it leaves the components to the organization. The lab uses a bare key pair it made itself, which shows the check but is not an organization-approved certificate. A real system uses a key the organization has approved and keeps its private half off the loading host.",
            "tieoff": "A record with no signature or a failed one is refused, as an edited record is.",
            "tool": "`cosign sign-blob` and `cosign verify-blob` (Step 2) with the key pair, as in GRC-4.",
        },
        {
            "control": "SR-4 Provenance",
            "feared": "Nobody can say where a model file came from or when it was approved, so a file of unknown origin is treated like an approved one.",
            "scope": "The model files that the loader accepts.",
            "question": "For this model file, what is recorded about its origin and contents, and who can change that record?",
            "evidence": "The signed record with the file name, source, hash and time.",
            "sufficient": "Each model file has one signed record that names its source and hash. NIST leaves the list of systems, components and data to the organization. The lab's source is the text lab-generated stand-in, because the file is a random stand-in and not a downloaded model. A real record names the supplier and the address the file was fetched from.",
            "tieoff": "A file with no record is not loaded. Keeping the record valid over time is a task for whoever owns the model.",
            "tool": "`jq` (Step 1) writes the record from the values you give it, and `date` stamps it.",
        },
    ],
    "terms": [
        ("Model file", "The saved numbers that make up a model, kept in a file. Real ones are very large; here a small random file stands in for one."),
        ("Supply chain", "Everything a system takes in from outside, such as libraries, images and model files, and the people and places they pass through before they reach you."),
        ("Hash", "A short fingerprint worked out from a file's contents. Change one byte of the file and the hash changes completely. Here it is SHA-256, written as 64 letters and digits."),
        ("Manifest", "A small file that lists what a model file should be: its name, source and hash. Here it is manifest.json."),
        ("Provenance", "The record of where something came from and who handled it."),
        ("Digital signature", "A mark made with a private key that anyone with the matching public key can check. It proves the signed bytes have not changed since the key holder signed them."),
        ("Key pair", "Two linked keys. The private key signs and stays secret; the public key checks signatures and can be shared."),
        ("Cosign", "A free tool for signing and checking signatures. Here it signs and checks the manifest."),
        ("Bundle", "The file Cosign writes next to what it signed. It holds the signature."),
        ("Tampering", "Changing something on purpose so that it behaves differently while looking the same."),
        ("Exit status", "A number a command leaves behind when it ends. 0 means success and anything else means a problem."),
        ("Heredoc", "A way to make a file by pasting its text between a first line such as cat > name <<'EOF' and a last line that says EOF."),
        ("Variable", "A named value that a command can use. The dollar sign in front of a name means use its value."),
        ("jq", "A tool that picks one value out of JSON text, or builds JSON text."),
        ("openssl", "A tool for cryptography. Here it works out the hash."),
        ("JSON", "A plain-text format for data: names and values written inside curly braces."),
    ],
    "concepts": [
        {
            "heading": "2.1 A model file is software that came from outside",
            "controls": [
                {"id": "SI-7 Software, Firmware, and Information Integrity"},
            ],
            "paras": [
                {"bullets": [
                    "A model file is run by the system, so a changed file changes what the system does. OWASP lists weak model provenance under supply chain risks (LLM03) and advises checking integrity with signing and file hashes.",
                    "The file's name and size say nothing about its contents, so the system compares a hash of the contents with the one that was approved.",
                    "A hash alone only helps if the expected hash cannot be changed by the same person who changed the file. Section 2.2 deals with that.",
                ]},
                {
                    "control": "SI-7: Software, Firmware, and Information Integrity",
                    "text": "The control asks the organization to employ integrity verification tools to detect unauthorized changes to the software, firmware and information it names, and to take defined actions when a change is detected. NIST leaves the list of what to check and the actions to the organization. This is done using:",
                },
                {"bullets": [
                    "`openssl dgst -sha256`: computes the hash of the model file, once when it is recorded and again every time it is loaded.",
                    "The loader load_model.py: compares the two hashes and refuses to load on a mismatch.",
                ]},
            ],
        },
        {
            "heading": "2.2 What a signature covers",
            "controls": [
                {"id": "CM-14 Signed Components"},
            ],
            "paras": [
                {"bullets": [
                    "A signature on the manifest proves the manifest is the one the key holder signed. It says nothing about the model file, which is a different file.",
                    "Step 3 shows this on purpose: the first loader checks only the signature and accepts a changed model file.",
                    "A lab key pair that you made yourself proves the mechanism, not that anyone approved the key.",
                ]},
                {
                    "control": "CM-14: Signed Components",
                    "text": "The control asks the system to prevent the installation of the components the organization names unless they have been digitally signed with a certificate the organization recognizes and approves. The components are chosen by the organization. This is done using:",
                },
                {"bullets": [
                    "`cosign sign-blob`: signs the manifest with the private key and writes the signature into a bundle file.",
                    "`cosign verify-blob`: checks the bundle against the manifest with the public key alone, so a loader needs no secret.",
                ]},
            ],
        },
        {
            "heading": "2.3 The record",
            "controls": [
                {"id": "SR-4 Provenance"},
            ],
            "paras": [
                {"bullets": [
                    "The manifest gives the loader and any later reader the file's name, its source, its hash and the time it was recorded.",
                    "Because it is signed, the record cannot be quietly rewritten to match a swapped file.",
                    "Keeping the record valid, for example when the file is replaced by a newer approved one, means signing a new record. The old record then stays as history.",
                ]},
                {
                    "control": "SR-4: Provenance",
                    "text": "The control asks the organization to document, monitor and maintain valid provenance of the systems, system components and data it names. The list is the organization's to define. This is done using:",
                },
                {"bullets": [
                    "manifest.json: written by `jq` from the file name, the source, the hash and the time.",
                    "The signature on it: stops the record being changed without the key.",
                ]},
                "The table lists the three checks the loader makes and what each one catches.",
            ],
            "table": {
                "headers": ["Check", "What it catches", "What it does not catch"],
                "rows": [
                    ("Signature on the manifest", "A manifest that was edited or never signed", "A model file that was swapped"),
                    ("Hash of the model file", "A model file that was changed or swapped", "A model that was approved and was bad from the start"),
                    ("Source in the manifest", "Nothing alone; it tells a reader where to look", "A false source that the signer wrote"),
                ],
            },
        },
    ],
    "steps": [
        {
            "title": "Make a stand-in model file and record where it came from",
            "learn": "Computing a hash and writing it into a record with the file's name, source and time gives the file an identity that you can check later.",
            "takeaway": "Record what a file should be at the moment you approve it, because you cannot work it out later from the file alone.",
            "controls": [
                {"id": "SR-4 Provenance", "how": "You write a manifest with the file name, its source, its hash and the time."},
                {"id": "SI-7 Software, Firmware, and Information Integrity", "how": "You compute the hash that the loader will compare against."},
            ],
            "why": "A real model file is many gigabytes. A random 4096 byte file stands in for it, because the checks work the same on any bytes. The record is written with jq so the values come from commands and not from typing.",
            "blocks": [
                {
                    "code": (
                        "mkdir -p /workspace/ai-2/model && cd /workspace/ai-2\n"
                        "head -c 4096 /dev/urandom > model/model.bin\n"
                        "SHA=$(openssl dgst -sha256 -r model/model.bin | cut -d' ' -f1)\n"
                        "jq -n --arg name model.bin --arg sha \"$SHA\" --arg source 'lab-generated stand-in' --arg made \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\" '{name: $name, sha256: $sha, source: $source, recorded: $made}' > model/manifest.json\n"
                        "cat model/manifest.json\n"
                        "test \"$(openssl dgst -sha256 -r model/model.bin | cut -d' ' -f1)\" = \"$(jq -r .sha256 model/manifest.json)\" && echo hash-matches"
                    ),
                    "label": "Make the file and write its record",
                    "intro": "You will now make the stand-in model file, work out its hash and write the manifest. The last command recomputes the hash and compares it with the manifest.",
                    "expect": "Example only. The hash and the time will differ, and so will the file.\n{\n  \"name\": \"model.bin\",\n  \"sha256\": \"9f2c...64 letters and digits...\",\n  \"source\": \"lab-generated stand-in\",\n  \"recorded\": \"2026-11-12T10:15:00Z\"\n}\nhash-matches",
                    "lines": [
                        ("mkdir -p /workspace/ai-2/model && cd /workspace/ai-2", "Makes a folder for this module, with a folder inside it for the model files, and moves into it.", "The files that are signed and loaded are kept apart from the keys."),
                        ("head -c 4096 /dev/urandom > model/model.bin", "Writes 4096 random bytes to a file.", "A random file stands in for a model file, since the checks only see bytes."),
                        ("openssl dgst -sha256 -r model/model.bin | cut -d' ' -f1", "Works out the SHA-256 hash of the file and keeps only the hash, not the file name that follows it.", "The hash is the file's fingerprint."),
                        ("jq -n --arg name ... --arg sha \"$SHA\" ...", "Builds a JSON object from the values you give it. --arg passes each value in as text.", "The values come from commands, so there is no typing error to hide a mismatch."),
                        ("--arg source 'lab-generated stand-in'", "Records the source. This is honest for a random file. A real record names the supplier and the address.", "Provenance is only worth having if it says where the file really came from."),
                        ("date -u +%Y-%m-%dT%H:%M:%SZ", "Prints the time in UTC in a standard form.", "The record shows when the file was approved."),
                        ("test \"$(...)\" = \"$(jq -r .sha256 model/manifest.json)\" && echo hash-matches", "Recomputes the hash and compares it with the one in the record. Prints hash-matches only if they are equal.", "This comparison is what the loader will do in Step 3."),
                    ],
                },
            ],
            "action": "Paste the block.",
            "checkpoint": "The manifest shows four fields and the last line prints hash-matches.",
        },
        {
            "title": "Sign the record and see what a signature covers",
            "learn": "Signing the manifest with a private key and checking it with the public key shows that an edited manifest no longer verifies, and why the signature alone does not protect the model file.",
            "takeaway": "Sign the record that names the hash, so whoever swaps the file cannot also swap the expected hash.",
            "controls": [
                {"id": "CM-14 Signed Components", "how": "You sign the manifest with a private key, verify it with the public key, and see an edited copy fail."},
            ],
            "why": "This is the same Cosign pattern as GRC-4: sign-blob writes a bundle, and verify-blob checks it with the public key alone. The key pair is made here, so the private key and its password stay in your working folder, and only the public key is used by the loader. The two flags that turn off the public transparency log are the ones GRC-4 uses.",
            "blocks": [
                {
                    "code": (
                        WORK
                        + "openssl rand -base64 24 > signing.pass\n"
                        "chmod 600 signing.pass\n"
                        "COSIGN_PASSWORD=\"$(cat signing.pass)\" cosign generate-key-pair\n"
                        "chmod 600 cosign.key\n"
                        + SIGN
                        + VERIFY.format(d="model") + "\n"
                        "mkdir -p edited && cp model/manifest.bundle.json edited/\n"
                        "jq '.source = \"somewhere-else\"' model/manifest.json > edited/manifest.json\n"
                        + VERIFY.format(d="edited") + "; echo \"exit status: $?\""
                    ),
                    "label": "Make a key pair, sign the record, verify it, and verify an edited copy",
                    "intro": "You will now make a key pair, sign the manifest, and verify it with the public key. You then change one field in a copy of the manifest and verify the copy against the original signature. The second verify must fail.",
                    "expect": "Example only. The wording of the messages may differ between Cosign releases.\nPrivate key written to cosign.key\nPublic key written to cosign.pub\nVerified OK\nError: invalid signature when validating ASN.1 encoded signature\nexit status: 1",
                    "lines": [
                        ("openssl rand -base64 24 > signing.pass", "Makes a random password and writes it to a file.", "The private key is protected by a password that nobody chose."),
                        ("chmod 600 signing.pass", "Makes the file readable by you only.", "The password opens the private key."),
                        ("COSIGN_PASSWORD=\"$(cat signing.pass)\" cosign generate-key-pair", "Makes cosign.key (private) and cosign.pub (public) in the current folder. The password is given to this one command through a variable, so Cosign does not ask for it. Unconfirmed: this writes both files without a prompt.", "The key pair is the identity that vouches for the record."),
                        ("cosign sign-blob --yes --key cosign.key --use-signing-config=false --tlog-upload=false --bundle model/manifest.bundle.json model/manifest.json", "Signs the manifest and writes the signature into the bundle file. The two flags keep it from using the public transparency log, which the lab does not have.", "This is the step that makes any later edit to the manifest detectable."),
                        ("cosign verify-blob --key cosign.pub --bundle model/manifest.bundle.json --insecure-ignore-tlog=true model/manifest.json", "Checks the signature with the public key alone and skips the log check.", "The check depends on nothing but the public key, so a loader needs no secret."),
                        ("mkdir -p edited && cp model/manifest.bundle.json edited/", "Makes a copy folder holding the original signature.", "You test an edit against a signature that was made for the original."),
                        ("jq '.source = \"somewhere-else\"' model/manifest.json > edited/manifest.json", "Changes one field in the copy.", "One changed field is enough to break the signature."),
                        ("; echo \"exit status: $?\"", "Prints the exit status of the verify before it. 1 means it refused.", "A loader decides by this number."),
                    ],
                },
            ],
            "action": "Paste the block.",
            "checkpoint": "The first verify prints Verified OK. The second prints an error and the exit status is 1.",
        },
        {
            "title": "Write the loader, find what it misses and add the hash check yourself",
            "learn": "A loader that checks only the signature accepts a changed model file, because the signature covers the manifest and not the file. Adding the hash check yourself closes that gap.",
            "takeaway": "Check the thing you are about to use, not only the paperwork about it.",
            "controls": [
                {"id": "SI-7 Software, Firmware, and Information Integrity", "how": "You add the hash comparison to the loader and see a changed file refused."},
                {"id": "CM-14 Signed Components", "how": "The loader verifies the manifest signature before it reads the manifest."},
            ],
            "why": "The first loader is supplied. It checks the signature and then loads. You change a copy of the model file and see it load, which is the gap. You then write the hash check yourself, as three lines. The reference answer is in the second block's lines table, so try before you read it.",
            "blocks": [
                {
                    "lang": "python",
                    "code": (
                        "import hashlib\n"
                        "import json\n"
                        "import subprocess\n"
                        "import sys\n"
                        "from pathlib import Path\n"
                        "\n"
                        "\n"
                        "def refuse(reason):\n"
                        "    print(\"refused: \" + reason)\n"
                        "    sys.exit(1)\n"
                        "\n"
                        "\n"
                        "def signature_ok(folder):\n"
                        "    command = [\n"
                        "        \"cosign\", \"verify-blob\", \"--key\", \"cosign.pub\",\n"
                        "        \"--bundle\", str(folder / \"manifest.bundle.json\"),\n"
                        "        \"--insecure-ignore-tlog=true\", str(folder / \"manifest.json\"),\n"
                        "    ]\n"
                        "    return subprocess.run(command, capture_output=True, text=True).returncode == 0\n"
                        "\n"
                        "\n"
                        "def main():\n"
                        "    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(\"model\")\n"
                        "    if not signature_ok(folder):\n"
                        "        refuse(\"the manifest signature did not verify\")\n"
                        "    manifest = json.loads((folder / \"manifest.json\").read_text())\n"
                        "    # hash check goes here\n"
                        "    print(\"loaded \" + manifest[\"name\"] + \" from \" + manifest[\"source\"])\n"
                        "\n"
                        "\n"
                        "main()\n"
                    ),
                    "label": "Read the first loader",
                    "intro": "You will now read the first loader, load_model.py, which a heredoc saves in the next block. It verifies the manifest signature and then loads. The comment marks the place where the hash check is missing. The next block saves it to a file for you.",
                    "expect": "Example only. Reading this block prints nothing.",
                    "lines": [
                        ("def refuse(reason): ... sys.exit(1)", "Prints why and ends the program with exit status 1.", "Every refusal looks the same to the caller: a printed reason and a status of 1."),
                        ("def signature_ok(folder)", "Runs the same cosign verify-blob command as Step 2 and returns true when its exit status is 0.", "The loader decides by the exit status and does not parse the message."),
                        ("capture_output=True, text=True", "Keeps the messages from Cosign out of the loader's output.", "Only the loader's own reason is shown."),
                        ("if not signature_ok(folder): refuse(...)", "Stops before reading the manifest if the signature fails.", "A manifest that is not trusted is not read."),
                        ("# hash check goes here", "Marks the missing check.", "Without it the loader trusts the file named in the manifest without looking at it."),
                    ],
                },
                {
                    "code": (
                        WORK
                        + "cat > load_model.py <<'EOF'\n"
                        "import hashlib\n"
                        "import json\n"
                        "import subprocess\n"
                        "import sys\n"
                        "from pathlib import Path\n"
                        "\n"
                        "\n"
                        "def refuse(reason):\n"
                        "    print(\"refused: \" + reason)\n"
                        "    sys.exit(1)\n"
                        "\n"
                        "\n"
                        "def signature_ok(folder):\n"
                        "    command = [\n"
                        "        \"cosign\", \"verify-blob\", \"--key\", \"cosign.pub\",\n"
                        "        \"--bundle\", str(folder / \"manifest.bundle.json\"),\n"
                        "        \"--insecure-ignore-tlog=true\", str(folder / \"manifest.json\"),\n"
                        "    ]\n"
                        "    return subprocess.run(command, capture_output=True, text=True).returncode == 0\n"
                        "\n"
                        "\n"
                        "def main():\n"
                        "    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(\"model\")\n"
                        "    if not signature_ok(folder):\n"
                        "        refuse(\"the manifest signature did not verify\")\n"
                        "    manifest = json.loads((folder / \"manifest.json\").read_text())\n"
                        "    # hash check goes here\n"
                        "    print(\"loaded \" + manifest[\"name\"] + \" from \" + manifest[\"source\"])\n"
                        "\n"
                        "\n"
                        "main()\n"
                        "EOF\n"
                        "python3 load_model.py model\n"
                        "mkdir -p tampered && cp model/manifest.json model/manifest.bundle.json tampered/\n"
                        "cp model/model.bin tampered/model.bin\n"
                        "echo x >> tampered/model.bin\n"
                        "python3 load_model.py tampered"
                    ),
                    "label": "Save the loader, load the real file, then load a changed copy",
                    "intro": "You will now save the loader, load the real file, and load a copy of the model file with one byte added. The copy has the real, correctly signed manifest next to it. The first loader should load it, and that is the gap.",
                    "expect": "Example only.\nloaded model.bin from lab-generated stand-in\nloaded model.bin from lab-generated stand-in",
                    "lines": [
                        ("cat > load_model.py <<'EOF'", "Saves the loader shown above as load_model.py. The quotes around EOF keep the shell from changing it.", "The file is the same one you just read."),
                        ("python3 load_model.py model", "Runs the loader on the real folder.", "The real file must load, or a refusal later proves nothing."),
                        ("mkdir -p tampered && cp model/manifest.json model/manifest.bundle.json tampered/", "Copies the signed manifest and its bundle into a new folder.", "The attacker in this test has the real, signed record."),
                        ("cp model/model.bin tampered/model.bin && echo x >> tampered/model.bin", "Copies the model file and adds one byte to the end.", "One byte is enough to change the hash."),
                        ("python3 load_model.py tampered", "Runs the loader on the copy. It loads, because the signature is fine and nothing looks at the file.", "This is the gap: a signature on the record does not cover the file."),
                    ],
                },
                {
                    "code": (
                        WORK
                        + "cat > hashcheck.txt <<'EOF'\n"
                        "    actual = hashlib.sha256((folder / manifest[\"name\"]).read_bytes()).hexdigest()\n"
                        "    if actual != manifest[\"sha256\"]:\n"
                        "        refuse(\"the model file does not match the signed hash\")\n"
                        "EOF\n"
                        "sed -i '/# hash check goes here/r hashcheck.txt' load_model.py\n"
                        "python3 load_model.py model\n"
                        "python3 load_model.py tampered; echo \"exit status: $?\""
                    ),
                    "label": "Add the hash check and run both loads again",
                    "intro": "You will now add the missing check. Write the three lines yourself first: read the model file named in the manifest, work out its SHA-256 hash with hashlib, and call refuse when it differs from the hash in the manifest. The block shows the answer in its lines table. Replace the lines in hashcheck.txt with your own and compare.",
                    "expect": "Example only.\nloaded model.bin from lab-generated stand-in\nrefused: the model file does not match the signed hash\nexit status: 1",
                    "lines": [
                        ("actual = hashlib.sha256((folder / manifest[\"name\"]).read_bytes()).hexdigest()", "The reference line. Reads the model file named in the manifest and works out its hash.", "The loader works out the hash itself, from the file it is about to load."),
                        ("if actual != manifest[\"sha256\"]: refuse(...)", "The reference check. Refuses when the hash it worked out is not the hash in the signed manifest.", "The signed manifest is the trusted side of the comparison, and the file is the side not yet trusted."),
                        ("sed -i '/# hash check goes here/r hashcheck.txt' load_model.py", "Inserts the contents of hashcheck.txt after the marker line.", "You add the check without retyping the file."),
                        ("python3 load_model.py tampered; echo \"exit status: $?\"", "Runs the loader on the changed copy and prints the exit status. 1 means it refused.", "The same copy that loaded before must now be refused."),
                    ],
                },
            ],
            "tip": "If you run the third block twice, the check is inserted twice. That still works. To start over, paste the second block again to rebuild load_model.py.",
            "action": "Read the loader, paste the second block, write the hash check, then paste the third block with your lines in hashcheck.txt.",
            "checkpoint": "Before the check, both loads print loaded. After it, the real folder loads and the tampered copy prints a refusal with exit status 1.",
        },
    ],
    "verify": [
        {
            "kind": "positive",
            "title": "The approved file loads",
            "controls": [
                {"id": "SR-4 Provenance", "how": "The loader prints the name and source from the signed record only after the checks pass."},
                {"id": "SI-7 Software, Firmware, and Information Integrity", "how": "The file hash matches the signed record, so the load proceeds."},
            ],
            "why": "Load the approved folder with the finished loader. If this fails, every refusal below could be a fault in the loader and not a check working.",
            "code": (
                WORK
                + "python3 load_model.py model; echo \"exit status: $?\""
            ),
            "expect": "Example only.\nloaded model.bin from lab-generated stand-in\nexit status: 0",
            "lines": [
                ("python3 load_model.py model", "Runs the finished loader on the approved folder.", "The right file must load."),
                ("echo \"exit status: $?\"", "Prints the exit status. 0 means it loaded.", "Success and refusal differ by this number."),
            ],
            "checkpoint": "It prints loaded and the exit status is 0.",
        },
        {
            "kind": "negative",
            "title": "A changed model file is refused",
            "controls": [
                {"id": "SI-7 Software, Firmware, and Information Integrity", "how": "A model file with one extra byte next to a correctly signed record is refused, so the hash check covers the file and not only the paperwork."},
            ],
            "why": "Load the copy whose model file has one extra byte. The record and signature are the real ones, so only the hash check can catch it.",
            "code": (
                WORK
                + "python3 load_model.py tampered; echo \"exit status: $?\"\n"
                "openssl dgst -sha256 -r tampered/model.bin | cut -c1-12\n"
                "jq -r .sha256 tampered/manifest.json | cut -c1-12"
            ),
            "expect": "Example only. The 12 characters will differ, and the two lines must not be equal.\nrefused: the model file does not match the signed hash\nexit status: 1\n3a91c07be2d4\n9f2c58a1d036",
            "lines": [
                ("python3 load_model.py tampered", "Loads the changed copy.", "It must be refused."),
                ("openssl dgst -sha256 -r tampered/model.bin | cut -c1-12", "Prints the first 12 characters of the changed file's hash.", "You see the hash that the loader worked out."),
                ("jq -r .sha256 tampered/manifest.json | cut -c1-12", "Prints the first 12 characters of the hash in the record.", "The two differ, which is why it was refused."),
            ],
            "checkpoint": "The loader refuses with exit status 1, and the two hash prefixes differ.",
        },
        {
            "kind": "negative",
            "title": "An edited record and a missing signature are refused",
            "controls": [
                {"id": "CM-14 Signed Components", "how": "A manifest edited to match a swapped file fails verification, and a manifest with no bundle fails too, so the loader trusts only a record the key holder signed."},
            ],
            "why": "An attacker who swaps the file will also edit the record to the new hash. Make that edit and load it, then remove the signature and load again. Both must be refused before the hash is even compared.",
            "code": (
                WORK
                + "NEWSHA=$(openssl dgst -sha256 -r tampered/model.bin | cut -d' ' -f1)\n"
                "jq --arg sha \"$NEWSHA\" '.sha256 = $sha' model/manifest.json > tampered/manifest.json\n"
                "python3 load_model.py tampered; echo \"edited record, exit status: $?\"\n"
                "mkdir -p unsigned && cp model/model.bin model/manifest.json unsigned/\n"
                "python3 load_model.py unsigned; echo \"no signature, exit status: $?\""
            ),
            "expect": "Example only.\nrefused: the manifest signature did not verify\nedited record, exit status: 1\nrefused: the manifest signature did not verify\nno signature, exit status: 1",
            "lines": [
                ("NEWSHA=$(openssl dgst -sha256 -r tampered/model.bin | cut -d' ' -f1)", "Works out the hash of the changed file.", "The attacker wants a record that agrees with the swapped file."),
                ("jq --arg sha \"$NEWSHA\" '.sha256 = $sha' model/manifest.json > tampered/manifest.json", "Writes a record whose hash matches the changed file. Its signature is the old one, made for the original record.", "The hash check would now pass, so only the signature can stop this."),
                ("python3 load_model.py tampered", "Loads the changed file with its edited record.", "The signature does not match the edited record, so the loader refuses."),
                ("mkdir -p unsigned && cp model/model.bin model/manifest.json unsigned/", "Makes a folder with the real file and record and no bundle.", "A record with no signature is the simplest fake."),
                ("python3 load_model.py unsigned", "Loads it. The signature check fails because the bundle is missing.", "No signature means not trusted."),
            ],
            "checkpoint": "Both loads print the signature refusal with exit status 1.",
        },
    ],
    "glossary": [
        ("Model file", "The saved numbers that make up a model, kept in a file."),
        ("Hash", "A short fingerprint worked out from a file's contents."),
        ("Manifest", "A small file that lists what a model file should be."),
        ("Provenance", "The record of where something came from."),
        ("Digital signature", "A mark made with a private key that a public key can check."),
        ("Key pair", "Two linked keys: a private key that signs and a public key that checks."),
        ("Bundle", "The file Cosign writes that holds the signature."),
        ("Tampering", "Changing something on purpose so it behaves differently."),
    ],
    "design": [
        {
            "decision": "Sign the record and check the file against it, not one or the other",
            "how": "The manifest holds the file's hash and is signed. The loader verifies the signature first, then recomputes the hash of the file and compares it with the signed one.",
            "why": "A hash with no signature can be replaced along with the file, and a signature on the record alone does not cover the file, so each check closes the gap in the other.",
            "alternatives": "Signing the model file itself is the alternative. Advantage: one check covers the file directly. Drawback: signing a very large file is slow, and the record still has to say where the file came from.",
        },
        {
            "decision": "Verify with the public key only, at load time",
            "how": "The loader holds cosign.pub and nothing secret. The private key and its password stay with whoever approves a file.",
            "why": "A loading host that is compromised cannot sign a fake record, because it does not hold the private key.",
            "alternatives": "Having the loader fetch a hash from a shared service is the alternative. Advantage: the expected hash can be changed centrally and quickly. Drawback: anyone who can change that service can change what is trusted, with no signature to show who did it.",
        },
        {
            "decision": "Refuse and exit with status 1, and do not repair or fall back",
            "how": "Any failed check prints one reason and ends the loader with status 1. It does not try an older file or skip the check.",
            "why": "A fallback turns a detected change into a silent one, which is the thing the checks exist to prevent.",
            "alternatives": "Loading the last good file when a check fails is the alternative. Advantage: the service keeps running. Drawback: the failure is hidden, and a repeated attack goes unnoticed unless something else raises it.",
        },
    ],
    "next": "Next module: Watch the Gateway and Respond: you read the gateway log for abuse, write a detection in Loki and a short runbook.",
}

MODULE["portability"] = {
    "bullets": [
        "The hash, the manifest and the loader are plain openssl, jq and Python and work on any OS with those tools.",
        "The signing uses Cosign with a local key pair; any signing tool that signs a file and verifies it with a public key can replace it.",
        "Lab-only values are the stand-in model file, the source text lab-generated stand-in and the key pair in your working folder.",
    ],
    "headers": ["Check/part", "In this lab (OpenShift)", "On other platforms", "What you change"],
    "rows": [
        ("Hash (`openssl dgst`)", "openssl in lab shell", "sha256sum or Get-FileHash", "The command; the idea is the same."),
        ("Record (manifest.json)", "Written with jq", "Any tool that writes JSON", "Name the real supplier and the address the file came from."),
        ("Signature (Cosign)", "Local key pair, no transparency log", "A key held in a key management service, or Sigstore with a log", "The key reference and whether to upload to a log."),
        ("Loader (load_model.py)", "python3 in lab shell", "Same on any OS with Python 3 and Cosign", "Nothing, except the path of the public key."),
    ],
}

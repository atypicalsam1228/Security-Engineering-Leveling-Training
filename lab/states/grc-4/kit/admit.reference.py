import json
import os
import subprocess

manifest = os.environ["MANIFEST"]
path = os.environ["CANDIDATE"] + "/" + manifest
run = subprocess.run(["oc", "apply", "--dry-run=server", "-n", "demo", "-f", path], capture_output=True, text=True)
result = "admitted" if run.returncode == 0 else "denied"
text = json.dumps({"manifest": manifest, "result": result, "message": run.stdout + run.stderr})
open(os.environ["EVIDENCE"] + "/policy-check.json", "w").write(text)
print(text)
raise SystemExit(0 if result == "admitted" else 1)

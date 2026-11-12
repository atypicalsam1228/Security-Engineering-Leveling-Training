# A deliberately poor measurement script, supplied so you can watch the review gate reject it.
import subprocess
import time

start = time.time()
subprocess.run(["oc", "create", "-f", "cases/ok.yaml"])
print(time.time() - start)

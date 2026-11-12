# Sends 60 requests from inside a pod to the db service and prints the median and p95 time in milliseconds.
# Run it through oc exec -i ... python3 - < latency.py, so nothing is copied into the pod.
import json
import statistics
import time
import urllib.request

samples = []
for _ in range(60):
    start = time.perf_counter()
    urllib.request.urlopen("http://db:8080", timeout=5).read()
    samples.append((time.perf_counter() - start) * 1000)
samples = sorted(samples[5:])
print(json.dumps({
    "n": len(samples),
    "median_ms": round(statistics.median(samples), 2),
    "p95_ms": round(samples[int(len(samples) * 0.95) - 1], 2),
}))

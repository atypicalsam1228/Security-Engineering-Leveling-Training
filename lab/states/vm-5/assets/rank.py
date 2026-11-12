"""Load Trivy findings and rank them."""
import json

SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}


def load_findings(path):
    with open(path, encoding="utf-8") as handle:
        report = json.load(handle)
    if not report.get("Results"):
        raise ValueError("report has no Results: the scan analyzed nothing")
    found = {}
    for result in report["Results"]:
        for vuln in result.get("Vulnerabilities") or []:
            scores = [s.get("V3Score", 0) for s in (vuln.get("CVSS") or {}).values()]
            found[(vuln["VulnerabilityID"], vuln["PkgName"])] = {
                "id": vuln["VulnerabilityID"],
                "package": vuln["PkgName"],
                "installed": vuln.get("InstalledVersion", ""),
                "fix": vuln.get("FixedVersion", ""),
                "severity": vuln.get("Severity", "UNKNOWN"),
                "score": max(scores, default=0.0),
            }
    return list(found.values())


def rank(findings):
    def key(item):
        return (-SEVERITY_ORDER.get(item["severity"], 0), -item["score"], not item["fix"], item["id"])

    return sorted(findings, key=key)

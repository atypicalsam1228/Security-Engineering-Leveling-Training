# ENG-1 live run (2026-11-10; run in parallel with GRC-4, timings not clean)

Every step and Test ran once and passed. No reset, no unblock fixes. `lab start eng-1` 8.2 s, INCOMPLETE notice (4 [live] items). Captures: `live-run/captures/ENG-1/`. Each wall time includes about 3 s of container start. About 90 s of command time against the module's 45 min.

| Step | Wall | Result |
| --- | --- | --- |
| 1a | 6.7 s | Matches; pod range 10.128.0.0/14, Service range 172.30.0.0/16 |
| 1b | 7.0 s | Matches: True, True, False |
| 2a | 8.5 s | Format mismatch: 200 x3, web-typo 000 exit 6 |
| 2b | 4.0 s | Mismatch (HTTP version); connected IP equals the Service IP |
| 3a | 5.4 s | Matches; Route created, edge termination |
| 3b | 5.7 s | Mismatch: plain curl exits 0, not 60 |
| 4a | 10.8 s | Matches; exit 28 |
| 4b | 5.5 s | Matches; allow-client allows `app=frontend`, client pod is `app=client` |
| 4c | 4.9 s | Matches; 28 became 7 |
| 4d | 6.3 s | Matches; targetPort 8081 vs container 8080, fixed, 200 |
| 5a, 5b | 3.0, 3.6 s | Match (31 lines; OK, 200, exit 0) |
| Test 1 | 4.7 s | Matches |
| Test 2 | 11.5 s | Matches |

## Bugs (none blocking)
1. **3b: exit 60 never appears.** The lab shell's CA bundle (`SSL_CERT_FILE`) trusts the router certificate (self-signed lab CA), so plain `curl https://<route>/` exits 0. The module teaches "60 means the certificate is not trusted here". Show the failure with an empty CA path (for example `curl --cacert /dev/null`) or drop the promise of 60.
2. **2a: extra text on the web-typo line.** oc prints "command terminated with exit code 6" on the same line as `000`, giving `web-typo: 000command terminated with exit code 6` then ` (curl exit 6)`. Example shows `web-typo: 000 (curl exit 6)`. Step 4 prints the same oc line, absent from the examples.
3. 2b: real output is `HTTP/1.0 200 OK` and `Server: SimpleHTTP/0.6 Python/3.11.13`, not `HTTP/1.1` with four lines.
4. 2b: `Connected to web (172.30.81.40) port 8080 (#0)` has a `(#0)` suffix.
5. Test 2: delete line reads `... "allow-client" deleted from net-lab namespace`.

## Notes
- TIP says "Next module: GRC-2" while the header says "Module 2 of 29"; check the intended successor.
- Left in the lab: namespace net-lab (client and web, Service web, Route web, both policies) and `~/net/hop_check.py`.

## TODO [live] status
Confirmed: network policy enforced (exit 28 with deny, 7 after the allow fix); default router cert and Route reachable on 443 (curl also trusts it without -k, see bug 1); client runs ubi9/ubi-minimal:9.5 with curl, web runs ubi9/python-311:1 as non-root uid.

## 2026-11-11 re-run
`lab start eng-1` 21.5 s (INCOMPLETE notice, 4 [live] items). Captures: `captures/ENG-1/r3-*.txt`. All steps and Tests 1-2 ran; one mismatch remains.

1. **Step 3b: exit code is 77, not 60.** The module's `curl -s --cacert /dev/null -o /dev/null "https://$host/"` now exits **77** ("error setting certificate file: /dev/null"), a bad CA file, not an untrusted issuer. Expected `curl exit: 60`. Plain curl exits 0 (lab shell trusts the lab CA). Verified alternative that gives 60: `env -u CURL_CA_BUNDLE -u SSL_CERT_FILE curl -s -o /dev/null "https://$host/"` (exit 60). `--cacert /etc/hostname` also gives 77. Suggested wording: replace the command with the `env -u ...` form and explain it removes the lab CA from curl's trust list; also fix the table row ("--cacert /dev/null gives curl an empty list" is wrong) and the exit-60 row text.
2. **Step 4a, 4c: extra line.** Real output has `command terminated with exit code 28` (4a) and `... exit code 7` (4c) before `exit:`. The NOTE under 2b mentions this, but the Expected blocks omit it. Suggested: add a line to Expected or add `2>/dev/null` to those curl calls.
3. **2b:** real output has a `(#0)` suffix on Connected and an extra `< Server: SimpleHTTP/0.6 Python/3.11.13` line (matches grep 'HTTP/'). Example is labelled "Example only"; cosmetic.
4. **Test 2:** delete line reads `... "allow-client" deleted from net-lab namespace`. Cosmetic.
5. 2a now matches the module exactly (`web-typo: 000 (curl exit 6)`; `2>/dev/null` fix works). 1a, 1b, 3a, 4b, 4d, 5a (31 lines), 5b, Test 1 match.

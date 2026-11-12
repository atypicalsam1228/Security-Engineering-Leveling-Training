# TODO: start state for CPS-2 (Apply a Hardening Baseline)

Lab needs are numbered as in the module's lab_needs list. `+ [done]` lines are covered by files in this folder;
`- [live]` lines can only be confirmed on a live cluster or account; `- [lab-build]` lines are provided by the lab build, not by start states.

+ [done] 1: Compliance Operator installed, ProfileBundles VALID (20-compliance-operator.sh).
+ [done] 2: sample-web and the supplied files exist (10-sample-web.sh, 30-baseline-files.sh).
- [live] 2: Rule names in 30-baseline-files.sh (ocp4-configure-network-policies-namespaces and the others) must exist on the installed Compliance Operator release; the script skips missing ones and fails below three.
- [live] 2: A TailoredProfile without an extends field needs the product-type annotation; confirm the scan reaches DONE.
- [live] 3: Pod security admission is enabled (OpenShift 4.12 or later) so the enforce label refuses bad-pod.yaml.

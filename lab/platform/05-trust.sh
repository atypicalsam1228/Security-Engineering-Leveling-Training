#!/usr/bin/env bash
# Trust for the in-lab services: writes the cluster ingress CA and a CA bundle (system CAs plus that CA).
# lab shell sees the bundle through SSL_CERT_FILE, CURL_CA_BUNDLE, GIT_SSL_CAINFO and REQUESTS_CA_BUNDLE.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
ca="$(ingress_ca_file)"
system=/etc/pki/tls/certs/ca-bundle.crt
[ -s "$system" ] || die "system CA bundle $system is missing in the tools image"
cat "$system" "$ca" >"$LAB_STATE_DIR/ca-bundle.crt"
lab_var_set LOKI_CA_FILE "$ca"
say "ingress CA saved at $ca; bundle saved at $LAB_STATE_DIR/ca-bundle.crt"

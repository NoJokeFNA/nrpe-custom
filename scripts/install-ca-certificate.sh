#!/usr/bin/env bash
# Runs before network package operations; the input is a BuildKit secret.
set -Eeuo pipefail

certificate="${1:?Expected optional CA secret path}"
expected="${2:?Expected certificate SHA-256 or none}"
if [[ ! -s "$certificate" ]]; then
  [[ "$expected" == none ]] || { echo 'ERROR: Selected CA certificate secret is missing' >&2; exit 1; }
  exit 0
fi
[[ "$expected" =~ ^[0-9a-f]{64}$ ]] || {
  echo 'ERROR: Select a CA with nrpe.py --ca-cert so its checksum invalidates the build cache' >&2; exit 1;
}
actual="$(sha256sum "$certificate")"
[[ "${actual%% *}" == "$expected" ]] || { echo 'ERROR: CA certificate checksum mismatch' >&2; exit 1; }
. /etc/os-release
case "$ID" in
  debian)
    install -D -m 0644 "$certificate" /usr/local/share/ca-certificates/nrpe-custom-company.crt
    if command -v update-ca-certificates > /dev/null; then
      update-ca-certificates
    else
      # Minimal Debian images lack the updater until ca-certificates is installed.
      # Add only the selected CA, preserving any existing system roots. Package
      # installation subsequently regenerates the full system trust database.
      mkdir -p /etc/ssl/certs
      cat "$certificate" >> /etc/ssl/certs/ca-certificates.crt
    fi
    ;;
  arch)
    install -D -m 0644 "$certificate" /etc/ca-certificates/trust-source/anchors/nrpe-custom-company.pem
    update-ca-trust
    ;;
  sles)
    install -D -m 0644 "$certificate" /etc/pki/trust/anchors/nrpe-custom-company.pem
    update-ca-certificates
    ;;
  *) echo "ERROR: Unsupported certificate trust store: $ID" >&2; exit 1 ;;
esac
echo 'PASS: Optional company CA installed; TLS verification remains enabled'

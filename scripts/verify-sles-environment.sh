#!/usr/bin/env bash
set -Eeuo pipefail
. /etc/os-release
[[ "$ID" == sles && "$VERSION_ID" == 12.3 && "$(uname -m)" == x86_64 ]] || {
  echo 'ERROR: Expected a genuine SLES 12 SP3 x86_64 environment' >&2
  exit 1
}
rpm --query --whatprovides 'libssl.so.1.0.0()(64bit)' > /dev/null
if [[ "${1:-build}" == runtime ]]; then
  for package in nrpe monitoring-plugins-nrpe gcc gcc48 rpm-build; do
    if rpm --query "$package" > /dev/null 2>&1; then
      echo "ERROR: Runtime base already contains $package; use a clean minimal image" >&2
      exit 1
    fi
  done
fi
echo 'PASS: Genuine SLES 12 SP3 with the original OpenSSL 1.0 ABI'

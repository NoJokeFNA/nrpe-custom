#!/usr/bin/env bash
set -Eeuo pipefail

. /etc/os-release
[[ "$ID" == sles && "$VERSION_ID" == 12.3 && "$(uname -m)" == x86_64 ]] || {
  echo 'ERROR: Expected SLES 12 SP3 on x86_64' >&2; exit 1;
}
shopt -s nullglob
packages=(/packages/nrpe-[0-9]*.x86_64.rpm)
(( ${#packages[@]} == 1 )) || {
  echo 'ERROR: Expected exactly one server RPM. Build this target first.' >&2; exit 1;
}
package="${packages[0]}"
cd /packages
sha256sum --check SHA256SUMS
grep -Fx -- "$(sha256sum "${package##*/}")" SHA256SUMS > /dev/null
[[ "$(rpm -qp --queryformat '%{NAME} %{ARCH}' "$package")" == 'nrpe x86_64' ]]
version="$(rpm -qp --queryformat '%{VERSION}-%{RELEASE}' "$package")"
[[ "$version" =~ \.withargs[0-9]+$ ]] || {
  echo "ERROR: Not a custom RPM version: $version" >&2; exit 1;
}
helpers=(/packages/system-user-nagios-*.noarch.rpm)
(( ${#helpers[@]} == 1 )) || { echo 'ERROR: Companion user-package RPM missing' >&2; exit 1; }
helper="${helpers[0]}"
grep -Fx -- "$(sha256sum "${helper##*/}")" SHA256SUMS > /dev/null
[[ "$(rpm -qp --queryformat '%{NAME} %{VERSION}-%{RELEASE} %{ARCH}' "$helper")" == 'system-user-nagios 1.0.0-0 noarch' ]]
rpm --upgrade --verbose "$helper"
getent passwd nagios > /dev/null

# Install only declared runtime requirements, not the build toolchain or an old
# NRPE server. rpmlib capabilities are supplied by RPM and checked at installation.
requirements="$(rpm -qp --requires "$package")"
provides="$(rpm -qp --provides "$package")"
dependencies=()
while IFS= read -r requirement; do
  if [[ "$requirement" == rpmlib\(* ]] || grep -Fxq -- "$requirement" <<< "$provides"; then
    continue
  fi
  dependencies+=("$requirement")
done <<< "$requirements"
for requirement in "${dependencies[@]}"; do
  rpm --query --whatprovides "$requirement" > /dev/null || {
    echo "ERROR: Missing pinned runtime dependency: $requirement" >&2; exit 1;
  }
done
# This RPM is our locally built artifact, verified against SHA256SUMS above.
# rpm still checks its payload digests and dependencies; repository packages
# continue to use normal zypper signature verification.
rpm --upgrade --verbose --hash "$package"
[[ "$(rpm -q --queryformat '%{VERSION}-%{RELEASE}' nrpe)" == "$version" ]]
clients=(/packages/monitoring-plugins-nrpe-*.x86_64.rpm)
(( ${#clients[@]} == 1 )) || { echo 'ERROR: Matching NRPE client RPM missing' >&2; exit 1; }
[[ "$(rpm -qp --queryformat '%{NAME} %{VERSION}-%{RELEASE} %{ARCH}' "${clients[0]}")" == "monitoring-plugins-nrpe $version x86_64" ]]
rpm --upgrade --verbose "${clients[0]}"
plugin_files="$(rpm -ql monitoring-plugins-nrpe)"
client=''
while IFS= read -r path; do
  if [[ "$path" == */check_nrpe && -x "$path" ]]; then
    [[ -z "$client" ]] || { echo 'ERROR: Multiple check_nrpe clients found' >&2; exit 1; }
    client="$path"
  fi
done <<< "$plugin_files"
[[ -n "$client" ]] || { echo 'ERROR: check_nrpe client not found' >&2; exit 1; }
export NRPE_TEST_TLS_VERSION=TLSv1.2
exec /opt/nrpe-test/test-nrpe-protocol.sh /etc/nrpe.cfg \
  "$client" /usr/sbin/nrpe "$version" sles12sp3 nrpe

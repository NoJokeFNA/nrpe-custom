#!/usr/bin/env bash
set -Eeuo pipefail

: "${DEBIAN_CODENAME:?Set DEBIAN_CODENAME via Compose}"
actual_codename="$(. /etc/os-release; printf '%s' "$VERSION_CODENAME")"
[[ "$actual_codename" == "$DEBIAN_CODENAME" ]] || {
  echo "ERROR: Expected ${DEBIAN_CODENAME}, running ${actual_codename}" >&2; exit 1;
}
[[ "$(dpkg --print-architecture)" == amd64 ]] || {
  echo 'ERROR: Integration tests require amd64' >&2; exit 1;
}

shopt -s nullglob
packages=(/packages/nagios-nrpe-server_*_amd64.deb)
(( ${#packages[@]} == 1 )) || {
  echo 'ERROR: Expected exactly one server package. Build this target first.' >&2; exit 1;
}
package="${packages[0]}"
cd /packages
sha256sum --check SHA256SUMS
grep -Fx -- "$(sha256sum "${package##*/}")" SHA256SUMS > /dev/null
[[ "$(dpkg-deb --field "$package" Package)" == nagios-nrpe-server ]]
[[ "$(dpkg-deb --field "$package" Architecture)" == amd64 ]]
version="$(dpkg-deb --field "$package" Version)"
[[ "$version" =~ \+withargs[0-9]+$ ]] || {
  echo "ERROR: Not a custom package version: $version" >&2; exit 1;
}

apt-get update
apt-get install -y --no-install-recommends "$package"
[[ "$(dpkg-query -W -f='${Version}' nagios-nrpe-server)" == "$version" ]]
exec /opt/nrpe-test/test-nrpe-protocol.sh /etc/nagios/nrpe.cfg \
  /usr/lib/nagios/plugins/check_nrpe /usr/sbin/nrpe "$version" "$DEBIAN_CODENAME" nagios-nrpe-server

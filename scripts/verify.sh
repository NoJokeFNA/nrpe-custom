#!/usr/bin/env bash
set -Eeuo pipefail

if (( $# != 3 )); then
  echo "Usage: $0 <deb-file> <source-config.h> <expected-version>" >&2
  exit 2
fi
package="$1"
config_h="$2"
version="$3"

[[ -s "$package" ]] || { echo "ERROR: Package missing or empty: $package" >&2; exit 1; }
[[ -s "$config_h" ]] || { echo "ERROR: Generated config.h missing: $config_h" >&2; exit 1; }

pkg_name="$(dpkg-deb --field "$package" Package)"
pkg_version="$(dpkg-deb --field "$package" Version)"
pkg_arch="$(dpkg-deb --field "$package" Architecture)"

[[ "$pkg_name" == 'nagios-nrpe-server' ]] || { echo "ERROR: Incorrect Package: $pkg_name" >&2; exit 1; }
[[ "$pkg_version" == "$version" ]] || { echo "ERROR: Incorrect Version: $pkg_version" >&2; exit 1; }
[[ "$pkg_arch" == 'amd64' ]] || { echo "ERROR: Incorrect Architecture: $pkg_arch" >&2; exit 1; }

grep -Eq '^#define[[:space:]]+ENABLE_COMMAND_ARGUMENTS[[:space:]]+1([[:space:]]|$)' "$config_h" || {
  echo 'ERROR: Compile configuration does not enable command arguments' >&2
  exit 1
}
if grep -Eq '^#define[[:space:]]+ENABLE_BASH_COMMAND_SUBSTITUTION[[:space:]]+1([[:space:]]|$)' "$config_h"; then
  echo 'ERROR: Dangerous Bash command substitution unexpectedly enabled' >&2
  exit 1
fi

# Ensure the resulting .deb contains the expected NRPE executable.
listing="$(dpkg-deb --contents "$package")"
if ! grep -Eq '/(sbin|bin)/nrpe$' <<< "$listing"; then
  echo 'ERROR: Server package appears not to contain the nrpe executable' >&2
  exit 1
fi

printf 'PASS: Package=%s Version=%s Architecture=%s, command arguments compiled in\n' \
  "$pkg_name" "$pkg_version" "$pkg_arch"

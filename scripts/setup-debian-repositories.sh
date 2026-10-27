#!/usr/bin/env bash
set -Eeuo pipefail

expected="${1:?Expected Debian codename}"
mode="${2:?Expected source or binary mode}"
actual="$(. /etc/os-release; printf '%s' "$VERSION_CODENAME")"
[[ "$actual" == "$expected" && ( "$mode" == source || "$mode" == binary ) ]] || {
  echo 'ERROR: Invalid Debian repository setup target or mode' >&2; exit 1;
}
sources=()
for file in /etc/apt/sources.list /etc/apt/sources.list.d/debian.sources; do
  [[ ! -f "$file" ]] || sources+=("$file")
done
(( ${#sources[@]} )) || { echo 'ERROR: Debian apt sources layout not recognized' >&2; exit 1; }

if [[ "$expected" == bullseye ]]; then
  # Bullseye security package files have moved to Debian's official archive.
  # Preserve the suite, signing keys, signature checks, and validity checks.
  sed -i -E 's@https?://(deb.debian.org|security.debian.org)/debian-security@http://archive.debian.org/debian-security@g' "${sources[@]}"
fi
if [[ "$mode" == source ]]; then
  if [[ -f /etc/apt/sources.list.d/debian.sources ]]; then
    sed -i -E '/^Types: / { /deb-src/! s/$/ deb-src/; }' /etc/apt/sources.list.d/debian.sources
  else
    sed -n '/^deb /s/^deb /deb-src /p' /etc/apt/sources.list > /etc/apt/sources.list.d/nrpe-source.list
  fi
fi

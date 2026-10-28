#!/usr/bin/env bash
# The SLE-12 RPM implementation validates every signature before installation.
set -Eeuo pipefail
directory="${1:?Expected pinned RPM directory}"
export LC_ALL=C
cd "$directory"
declare -A hashes=() verified=()
while IFS= read -r line; do
  [[ "$line" =~ ^([0-9a-f]{64})\ \ ([A-Za-z0-9][A-Za-z0-9._+~-]*\.rpm)$ ]] || {
    echo 'ERROR: Invalid pinned RPM checksum entry' >&2; exit 1;
  }
  file="${BASH_REMATCH[2]}"
  [[ ! ${hashes[$file]+present} ]] || { echo 'ERROR: Duplicate RPM checksum entry' >&2; exit 1; }
  hashes[$file]="${BASH_REMATCH[1]}"
done < SHA256SUMS
sha256sum --check SHA256SUMS
while IFS=$'\t' read -r file name version architecture vendor key; do
  [[ "$file" =~ ^[A-Za-z0-9][A-Za-z0-9._+~-]*\.rpm$ && "$key" =~ ^[0-9a-f]{8}$ ]] || {
    echo 'ERROR: Invalid pinned RPM identity' >&2; exit 1;
  }
  [[ ${hashes[$file]+present} && ! ${verified[$file]+present} ]] || {
    echo 'ERROR: Missing checksum or duplicate RPM identity' >&2; exit 1;
  }
  signature="$(rpmkeys --checksig --verbose "$file")"
  grep -Eiq "Signature, key ID ${key}: OK" <<< "$signature" || {
    echo "ERROR: Required SUSE signature is missing: $file" >&2; exit 1;
  }
  actual="$(rpm -qp --queryformat '%{NAME} %{VERSION}-%{RELEASE} %{ARCH}|%{VENDOR}' "$file")"
  [[ "$actual" == "$name $version $architecture|$vendor" ]] || {
    echo "ERROR: Unexpected SUSE RPM identity: $file" >&2; exit 1;
  }
  verified[$file]=1
  echo "PASS: Original SUSE signature, hash and identity: $file"
done < IDENTITIES.tsv
shopt -s nullglob
files=(*.rpm)
(( ${#files[@]} > 0 && ${#files[@]} == ${#verified[@]} && ${#verified[@]} == ${#hashes[@]} )) || {
  echo 'ERROR: Unreviewed or missing RPMs in native input directory' >&2; exit 1;
}
for file in "${files[@]}"; do
  [[ ${verified[$file]+present} ]] || { echo "ERROR: Unverified RPM: $file" >&2; exit 1; }
done

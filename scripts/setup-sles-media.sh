#!/usr/bin/env bash
set -Eeuo pipefail

media="${1:?Expected installation media directory}"
[[ -d "$media" ]] || exit 0
listing="$(find "$media" -type f -path '*/repodata/repomd.xml' -print)"
[[ -n "$listing" ]] || exit 0

# Check the product identity again for direct Compose users, not only CLI users.
metadata_listing="$(find "$media" -maxdepth 2 -type f \
  \( -name content -o -path '*/[Mm]edia.1/[Mm]edia' -o -path '*/[Mm]edia.1/products' \) -print)"
[[ -n "$metadata_listing" ]] || { echo 'ERROR: SLES product metadata missing from media' >&2; exit 1; }
mapfile -t metadata <<< "$metadata_listing"
grep -Eiq '(SUSE.*Linux.*Enterprise|\bSLE[-_ ])' "${metadata[@]}" || {
  echo 'ERROR: Expected official SLES installation media' >&2; exit 1;
}
grep -Eiq '\b15[. _-]*(SP[ _-]*)?4\b' "${metadata[@]}" || {
  echo 'ERROR: Expected SLES 15 SP4 installation media' >&2; exit 1;
}
if grep -Eiq '\bopenSUSE\b' "${metadata[@]}"; then
  echo 'ERROR: Leap/openSUSE media are not allowed for the pure SLES target' >&2; exit 1
fi
grep -Eq '\bx86_64\b' "${metadata[@]}" || {
  echo 'ERROR: Expected x86_64 installation media' >&2; exit 1;
}
[[ -f "$media/Module-Basesystem/repodata/repomd.xml" ]] || {
  echo 'ERROR: Full Media1 with Module-Basesystem is required' >&2; exit 1;
}

index=0
while IFS= read -r file; do
  directory="${file%/repodata/repomd.xml}"
  relative="${directory#"$media"}"
  case "$relative" in
    ''|/Module-Basesystem|/Module-Server-Applications|/Module-Development-Tools|/Module-Legacy|/Product-SLES) ;;
    *) continue ;; # Do not activate HA, SAP, HPC, desktop, or other products.
  esac
  [[ -f "${file}.asc" ]] || { echo "ERROR: Repository signature missing: ${file}.asc" >&2; exit 1; }
  case "$(readlink -f "$directory")" in
    "$media"|"$media"/*) ;;
    *) echo 'ERROR: Media repository escapes the mounted directory' >&2; exit 1 ;;
  esac
  index=$((index + 1))
  # Online matching SLES updates take precedence; media provide missing modules.
  zypper --non-interactive addrepo --priority 200 "dir:$directory" "nrpe-sles-media-$index"
done <<< "$listing"
echo "PASS: Registered $index signed SLES 15 SP4 media repositories"

#!/usr/bin/env bash
set -Eeuo pipefail

. /etc/os-release
[[ "$ID" == sles && "$VERSION_ID" == 15.3 && "$(uname -m)" == x86_64 ]] || {
  echo 'ERROR: This image must be SLES 15 SP3 on x86_64' >&2; exit 1;
}
bash "$(dirname "$0")/setup-sles-media.sh" /mnt/nrpe-sles-media
# Package Hub's archived SP3 backports, not SP7 or a replacement OS image.
zypper --non-interactive addrepo --refresh --priority 300 \
  https://download.opensuse.org/repositories/openSUSE:/Backports:/SLE-15-SP3/standard/ \
  nrpe-sp3-backports
# Repository keys are obtained over verified HTTPS; signature checks stay enabled.
zypper --non-interactive --gpg-auto-import-keys refresh

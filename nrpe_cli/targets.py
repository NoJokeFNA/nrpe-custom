"""Target-specific package conventions shared by every controller command."""

TARGET_CONFIG = {
    name: {"pattern": "nagios-nrpe-server_*_amd64.deb",
           "prefix": "nagios-nrpe-server_", "suffix": "_amd64.deb"}
    for name in ("debian11", "debian12", "debian13", "debian14")
}
TARGETS = tuple(TARGET_CONFIG)


def package_files(root, target):
    return sorted((root / "output" / target).glob(TARGET_CONFIG[target]["pattern"]))

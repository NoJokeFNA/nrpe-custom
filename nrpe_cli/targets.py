"""Target-specific package conventions shared by every controller command."""

TARGET_CONFIG = {
    name: {"pattern": "nagios-nrpe-server_*_amd64.deb",
           "prefix": "nagios-nrpe-server_", "suffix": "_amd64.deb"}
    for name in ("debian11", "debian12", "debian13", "debian14")
}
TARGET_CONFIG["sles12sp3"] = {
    "pattern": "nrpe-[0-9]*.x86_64.rpm", "prefix": "nrpe-", "suffix": ".x86_64.rpm",
}
DEFAULT_TARGETS = tuple(TARGET_CONFIG)
TARGET_CONFIG["archlinux"] = {
    "pattern": "nrpe-[0-9]*-x86_64.pkg.tar.zst", "prefix": "nrpe-", "suffix": "-x86_64.pkg.tar.zst",
}
TARGETS = tuple(TARGET_CONFIG)
ARCH_NOTICE = ("Optional Arch build: compiles arguments contrary to the former distribution security policy. "
               "Arguments stay disabled by default; review docs/archlinux.md before deployment.")


def package_files(root, target):
    return sorted((root / "output" / target).glob(TARGET_CONFIG[target]["pattern"]))

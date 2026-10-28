"""Validate a local, extracted SLES installation medium before Docker uses it."""

from pathlib import Path
import re

MODULES = {"Module-Basesystem", "Module-Server-Applications", "Module-Development-Tools",
           "Module-Legacy", "Product-SLES"}


def validate_media(value):
    root = Path(value).expanduser().resolve()
    if not root.is_dir():
        raise RuntimeError("SLES media must be an extracted directory, not an ISO file or missing path.")
    # Read distribution metadata only; do not read RPM payloads or arbitrary files.
    metadata = list(root.glob("[Mm]edia.1/[Mm]edia"))
    metadata += list(root.glob("[Mm]edia.1/products"))
    metadata += list(root.glob("content"))
    metadata += list(root.glob("*/content"))
    chunks = []
    for path in metadata:
        if not path.resolve().is_relative_to(root):
            raise RuntimeError("Media metadata escape the selected directory through a symlink.")
        if path.is_file():
            with path.open(encoding="utf-8", errors="replace") as source:
                chunks.append(source.read(65536))
    text = "\n".join(chunks)
    if not re.search(r"(?:SUSE.*Linux.*Enterprise|\bSLE[-_ ])", text, re.I):
        raise RuntimeError("The media directory has no SLES product metadata. Extract the full official medium.")
    if not re.search(r"\b15[. _-]*(?:SP[ _-]*)?3\b", text, re.I):
        raise RuntimeError("The installation medium must identify SLES 15 SP3.")
    if re.search(r"\bopenSUSE\b", text, re.I):
        raise RuntimeError("openSUSE installation media are not accepted for this pure SLES target.")
    if not re.search(r"\bx86_64\b", text):
        raise RuntimeError("The SLES medium must be for x86_64, not ARM, Power, or Z Systems.")
    if not (root / "Module-Basesystem/repodata/repomd.xml").is_file():
        raise RuntimeError("Use Full Media1 with Module-Basesystem, not the small Online installer.")
    repositories = [root / "repodata/repomd.xml"]
    repositories += [root / module / "repodata/repomd.xml" for module in sorted(MODULES)]
    repositories = [path for path in repositories if path.is_file()]
    for path in repositories:
        if not path.resolve().is_relative_to(root):
            raise RuntimeError("A media repository escapes the selected directory through a symlink.")
        signature = path.with_name("repomd.xml.asc")
        if not signature.resolve().is_relative_to(root):
            raise RuntimeError("A repository signature escapes the selected media directory.")
        if not signature.is_file():
            raise RuntimeError(f"Missing repository signature: {path.parent / 'repomd.xml.asc'}")
    return root

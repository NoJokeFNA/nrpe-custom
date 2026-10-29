# Cleaning local workflow data

`clean` previews eligible data by default. It does not install packages, change
the target server, remove current packages or contact Docker unless an image is
explicitly selected.

The terminal menu exposes the same options under **Local cleanup**. It shows
the read-only preview before a separate deletion confirmation, defaults to
cancellation and rejects a changed candidate list until it is previewed again.

```sh
python3 nrpe.py clean
python3 nrpe.py clean --older-than 60 --keep-runs 10
```

The defaults are 30 days and at least five retained runs. Only completed,
recognized run directories containing `report.json` and optionally `run.log`
are candidates. Both completion time and file modification times must be old
enough. Running, malformed and unrecognized evidence is left for inspection.

The newest report for each current target and the newest test report matching
its current package bytes are retained even with `--keep-runs 0`. The newest
complete successful `verify` report matching those bytes is also retained,
even if a newer runtime-only test exists. Current target output directories,
release candidates, downloaded releases, locks, certificates
and arbitrary working directories are never cleanup candidates. Back up evidence
you need beyond that retention policy before deleting it.

## Apply an inspected selection

```sh
python3 nrpe.py clean --older-than 60 --keep-runs 10 --apply
```

`--apply` is explicit deletion consent, including in non-interactive use. The
tool recalculates the plan under a maintenance guard; changed candidates abort
the operation. Active or unresolved target locks block deletion. New controller
workflows cannot acquire target locks during cleanup. Symlinks, Windows reparse
points and special files in traversed cleanup paths are rejected.
Mounted candidate directories and nested mount points are rejected too.

Cleanup is sequential, not a filesystem transaction: an I/O or Docker error can
leave a partially completed cleanup. Already removed paths are reported. Inspect
the error and preview again; do not assume everything was deleted.

Direct Compose commands do not take controller locks. Do not run them against
the same workspace while applying cleanup. After a crash, a retained
`.nrpe/locks/maintenance` directory must be inspected along with processes and
containers before manually removing that marker. Never remove a live lock.

## Individually selected Docker images

```sh
python3 nrpe.py clean --image nrpe-custom-builder:sles12sp3
python3 nrpe.py clean --image nrpe-custom-builder:sles12sp3 --apply
```

Repeat `--image` to select more than one explicit `nrpe-custom` builder/test
image tag. Docker is required for the preview too. Base images, bare IDs and
wildcards are rejected. Images used by running **or stopped** containers are
refused; identity and usage are checked again before applying. Removal uses
`docker image rm` without force. A concurrent Docker change can still cause
Docker to refuse deletion; the tool does not override that protection.

This command does not prune Docker globally or remove containers, networks,
volumes or BuildKit caches. Removing an image tag may reclaim little space when
layers are shared. Manage Docker Desktop/Engine storage separately if necessary.

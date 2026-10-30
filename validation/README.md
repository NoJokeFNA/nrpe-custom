# Distribution-package research

`probe-installed-nrpe.sh` is a research harness for an already installed regular
NRPE server/client package in a fresh disposable Linux container. It is not a
new supported build target or a production diagnostic. Use
`scripts/diagnose-server.sh` for read-only inspection of a real server.

The probe requires container root and `NRPE_DISPOSABLE_PROBE=1`. Do not set that
marker on an existing/shared container or a production system. Install the exact
package through the matching distribution's normal repositories first, preserving
TLS and package-signature checks. The image must contain `/bin/echo`, a real
package-provided `nrpe` or `nagios` account, NRPE 4.x and its `check_nrpe` client.
Do not publish any container ports. Provide HTTPS trust only to the package
manager that needs it; never disable verification to get an install to work.

Run the reviewed helper inside that disposable container:

```sh
NRPE_DISPOSABLE_PROBE=1 sh /run/probe-installed-nrpe.sh
```

Mount/copy this helper to that path first. It creates a temporary configuration,
starts the installed daemon in foreground mode on IPv4 loopback port 15666, and
defaults to plaintext on both ends solely to isolate argument handling. Port 15666 must
be unused. A successful fixed-command baseline is required for each of two
runtime policies. Arguments must be rejected with `dont_blame_nrpe=0`; with `1`,
the probe records whether the exact supplied ALPHA/BETA pair is returned. It
keeps Bash substitution disabled and removes only its temporary configuration
and own daemon on exit. It does not change packaged configuration or install
packages. All container contents should be discarded afterwards.

For a certificate-authenticated TLS 1.2 probe, also install the distribution's
`openssl` CLI and select TLS explicitly:

```sh
NRPE_DISPOSABLE_PROBE=1 NRPE_PROBE_TRANSPORT=tls sh /run/probe-installed-nrpe.sh
```

This mode creates short-lived, container-only test certificates, requires a
trusted client certificate on the daemon, and verifies the server certificate
with `check_nrpe -A`. It uses authenticated ECDHE/DHE-RSA with anonymous/null ciphers
excluded. `ssl_use_adh=1` initializes finite-field DH on older NRPE versions;
the cipher list and client `-d 0` exclude anonymous authentication. These are
probe settings, not changes to a packaged default. Both argument policies run
over TLS. Wrong server trust and a missing client certificate must be rejected;
a subsequent valid baseline must still succeed. A single temporary certificate
is shared by both ends to keep this local capability check small: it does not
validate production PKI roles, hostname verification, revocation or TLS 1.3.

Exit 0 means the observation completed, not that argument support exists: inspect
`ARGUMENT_CAPABILITY`. `not_demonstrated` requires recipe/binary/log investigation;
it is not by itself proof of a compile-time omission. A failed baseline or an
argument request unexpectedly accepted while disabled fails the probe.

Record image tag **and digest**, OS/release/architecture, package version/source,
binary hashes, exact results and scope. Image digests do not pin a later package
repository transaction. The default plaintext mode establishes no TLS result. The optional TLS mode
establishes only the described local certificate checks. Neither mode establishes
systemd/OpenRC boot, plugin coverage, upgrade or rollback results. See the
[dated review](../docs/package-reviews/2026-10-30.md) and
[compatibility matrix](../docs/package-compatibility.md).

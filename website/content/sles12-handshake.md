# When the OS version was the missing detail

**Field note · 28 October 2026 · SLES 12 SP3 · NRPE 2.15 / check_nrpe 4.1.0**

This account is based on the operator's reported commands and output during
troubleshooting. Hostnames and addresses are anonymized. It is an observation
from one deployment, not a recommendation to disable production TLS.

## The symptom

The daemon logged `Error: Could not complete SSL handshake. 1`. The initial
discussion assumed SLES 15. Checking `/etc/os-release`, the installed RPM and
linked libraries changed the picture: the host actually ran **SLES 12 SP3**, NRPE
`2.15-4.24` and OpenSSL `1.0.2j-fips` with the OpenSSL 1.0 ABI.

That mattered. A package built for SLES 15 could not be treated as a compatible
replacement. Modern configuration directives also did not add certificate
authentication support to the existing NRPE 2.15 executable.

## A smaller test, on a separate port

The operator started a second daemon with a minimal configuration on port 15666,
leaving the managed service on 5666 unchanged. Both client and test daemon used
`-n`; the client also used `-2` for the old NRPE packet format.

There were useful mistakes along the way: commands were initially run on a
different host, a configured bind address was not local to that machine, and
the test config's group permissions prevented the service user from reading it.
On the intended server, NRPE 2.15 also rejected `-f`; this version needed `-d`.

Once those details were corrected, the reported response was:

```text
NRPE_PLAIN_OK
```

The [full isolated procedure](../../docs/sles12sp3-plaintext-diagnostic.md)
records the configuration, checks and cleanup without requiring a systemd reload.

## What the result established

The separate test confirmed basic NRPE communication and execution of a fixed
command without TLS. A later temporary plaintext test on port 5666 also returned
`NRPE v2.15` and a successful `check_load` response with supplied thresholds.

This narrowed the original problem toward TLS negotiation. It did **not** identify
the exact cipher/certificate cause or prove a lasting TLS fix. Starting a manual
daemon also did not make it a systemd-managed service: a second managed start
failed because another NRPE process was already running.

## The next step was a different build, not a weaker default

The project now targets genuine SLES 12 SP3. Its NRPE 4.1.1 container checks cover
certificate-authenticated TLS 1.2 against the original OpenSSL ABI; a separate
modern OpenSSL client test also passed with server identity verification and a
required client certificate. Those are separate test environments, not proof of
installation on this operator's server.

See the [SLES TLS policy](../../docs/configuration-examples.md#hosts-tls-and-fixed-commands)
and [validation limits](../../docs/practical-validation.md) before deployment.
Temporary plaintext instances should be stopped and the intended managed service
restored; no successful production upgrade or rollback is claimed in this note.

## The lesson to carry forward

Verify the host and OS before choosing a build target. Record the daemon and
client versions, then test the smallest useful hypothesis. A successful plain
connection is evidence about connectivity — not evidence that TLS is configured.

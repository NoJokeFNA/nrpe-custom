# Frequently asked questions

For log analysis, see [troubleshooting](troubleshooting.md). Use
`python3 nrpe.py diagnose ./redacted-nrpe.log --context nrpe` for an existing
daemon/client log, or omit the context for build/download failures.

## Which SLES version does this project target?

**SLES 12 SP3**, confirmed by `/etc/os-release`. Earlier references to SLES 15
SP3/SP4 were based on an incorrect platform assumption. Neither their RPMs nor
their successful tests establish compatibility with SLES 12. The active target
is `sles12sp3`; see the [native build guide](sles12sp3.md).

The reported server runs NRPE `2.15-4.24`, linked to OpenSSL's 1.0 ABI. That old
NRPE advertises anonymous DH, not modern certificate authentication. A newer
NRPE/client built for SLES 12 can use certificate-authenticated TLS 1.2 with the
original OpenSSL 1.0.2 library. TLS 1.3 requires a newer TLS library and is not
provided by this build. `disable_syslog=0` is unknown to the old daemon;
commenting it out removes the warning but does not fix TLS compatibility.

The message `Could not complete SSL handshake. 1` alone does not identify a
specific cipher, certificate or trust failure. Compare the actual server/client
versions, command, TLS settings and simultaneous logs. Do not disable encryption
or certificate verification to hide the error. Build-time `--ca-cert` affects
source downloads, not the deployed NRPE certificate configuration.

To isolate this on SLES 12 SP3 before upgrading, the
[temporary plaintext diagnostic](sles12sp3-plaintext-diagnostic.md) documents the
user's successful NRPE 2.15 / `check_nrpe` 4.1.0 test on a separate port. It
includes anonymized examples, the encountered errors and cleanup; it does not
recommend disabling TLS in production.

For NRPE 4.1.1 on SLES 12, also review the
[authenticated DHE-RSA example](configuration-examples.md#hosts-tls-and-fixed-commands).
With this old OpenSSL integration, `ssl_use_adh=0` skips DH initialization and
can produce `no shared cipher` with modern clients. Use the complete documented
policy, which explicitly excludes anonymous ciphers, rather than enabling ADH
alone. It was tested against OpenSSL 3.5.7 with certificate verification intact.

## Which services must run on a combined Nagios and NRPE server?

When Nagios Core and the NRPE daemon are installed on the same SLES server, and
the installed units are named `nagios.service` and `nrpe.service`, enable and
start each service:

```sh
sudo systemctl enable --now nagios.service
sudo systemctl enable --now nrpe.service
systemctl is-active nagios.service nrpe.service
```

`enable --now` configures startup at boot and starts the service immediately.
Both should report `active` for this combined setup. If a unit is missing or
fails, inspect the installed unit names and logs before replacing packages:

```sh
systemctl list-unit-files nagios.service nrpe.service
sudo systemctl status nagios.service nrpe.service --no-pager
sudo journalctl -u nagios.service -u nrpe.service -n 100 --no-pager
```

Package-provided service names vary. For the custom Debian server package in
this project, the NRPE unit is `nagios-nrpe-server.service`:

```sh
sudo systemctl enable --now nagios-nrpe-server.service
```

Follow the [official Nagios Core documentation](https://assets.nagios.com/downloads/nagioscore/docs/nagioscore/4/en/)
and [NRPE documentation](https://github.com/NagiosEnterprises/nrpe) for complete
installation and deployment configuration. Enabling a service does not install
missing plugins, provision TLS credentials or configure monitoring checks.

## Does a separate NRPE agent also need Nagios Core locally?

No. Nagios Core schedules checks on the monitoring server. Its `check_nrpe`
client contacts the NRPE daemon on the monitored host, which executes the
configured local plugins. A host used only as an NRPE agent needs its NRPE
daemon and required plugins, but does not need a local Nagios scheduler.
Starting Nagios alone does not start a separately packaged NRPE daemon.

The two-service command above applies to the combined server, not every NRPE
agent. See the [connection map](network.md#connection-map) for the separate roles.

## When do I actually need a custom build?

First distinguish service/configuration problems from missing compiled features:

1. Check that the intended NRPE service is running and inspect its logs.
2. Confirm the monitoring server can reach NRPE with the intended allowed hosts,
   firewall rules and TLS configuration.
3. Confirm that the configured plugin exists and runs as the NRPE service user.
4. If arguments are required, check both the package's compiled support and the
   runtime policy. `dont_blame_nrpe=0` intentionally rejects arguments even when
   support was compiled in. Enable arguments only after reviewing the command
   definitions and validating permitted inputs.

If the distribution package already provides the required feature, use its
supported packaging and configure the deployment. A stopped service or an
argument-disabled runtime setting alone is not a reason to compile another
binary. This project's Debian build is for deployments that deliberately need
compiled command-argument support; it preserves disabled runtime arguments by
default and disabled Bash command substitution.

After changing configuration, restart the applicable NRPE service and repeat
the actual remote check. `enable --now` does not restart an already active
service to reload modified configuration. See [installation](installation.md)
and [deployment security](security.md) for this project's custom package scope.

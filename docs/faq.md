# Frequently asked questions

## Which SLES service pack does this project target?

The maintainer corrected the affected deployment to **SLES 15 SP3** on
2026-10-28. The earlier automation targeted SP4, not SP5. The SLES build now uses
a genuine SP3 base and matching dependencies; see the
[SLES target guide](sles15sp3.md) for actual validation evidence.

Service startup and compiled argument support are separate concerns. The service
checks below help diagnose startup problems; they do not establish that a custom
build is unnecessary on SP3. Historical SP4 release assets are not overwritten
or relabeled as SP3 packages.

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

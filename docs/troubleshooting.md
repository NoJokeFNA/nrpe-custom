# Build and NRPE diagnostics

Failed workflow commands retain their original exit status and raw output in
the local run log. Recognized failures add contextual hints. Successful commands
do not emit failure hints, including when a retry recovered from an earlier
error. Hints classify observed messages; they do not establish a root cause.

## Read-only target-server inspection

Copy the reviewed `scripts/diagnose-server.sh` onto the monitored Linux host;
it requires Bash and standard Linux tools, not Python or Docker. For SLES:

```sh
bash scripts/diagnose-server.sh --config /etc/nrpe.cfg \
  --unit nrpe.service --monitor-ip 192.0.2.10
```

For Debian:

```sh
bash scripts/diagnose-server.sh --config /etc/nagios/nrpe.cfg \
  --unit nagios-nrpe-server.service --monitor-ip 192.0.2.10
```

Replace the documentation address with the actual monitoring source. It checks
OS identity, the daemon version and package owner, service/startup state,
listeners, configuration/includes, relevant TLS settings and configured plugin
executables. It never sources the configuration or executes plugins, installs
packages, restarts services or changes the firewall. Command arguments and key
contents are not printed. Complex executable expressions are flagged for manual
review instead of evaluated. Existing files do not prove successful plugin or
TLS operation.

Run without root first. Where authorized, running with `sudo bash ...` also lets
it check configuration/plugin access as the systemd service user using `runuser`.
Missing permissions/tools are reported; they are not a successful validation.
Exit 1 means failed checks, 2 means invalid usage, and 0 means no failed checks;
review all warnings even on exit 0. Output can contain private file paths and
listener addresses: review/redact it before sharing. Remote reachability,
firewall rules and certificate authentication require separate tests below.

## Inspect an existing log

```sh
python3 nrpe.py diagnose ./build.log
python3 nrpe.py diagnose ./build.log --ca-configured
python3 nrpe.py diagnose ./redacted-nrpe.log --context nrpe
```

`diagnose` reads a local text file without Docker or a connection to the server.
It executes no log content, prints category hints rather than raw lines, and
does not mark any workflow as passed. Exit 0 means the file was read successfully,
not that the recorded build/check succeeded. No recognized failure is not a pass.
Use `--ca-configured` only when the recorded build was actually given a CA.

The default context is build/download failures. Use `--context nrpe` for daemon
or `check_nrpe` logs: build-time CA configuration and deployed client/server TLS
are separate. On servers without Python, review/redact the log and copy it to
the workstation running this tool. Never share credentials, private keys or full
environment dumps. Keep raw local logs outside Git.

## Interpret the categories

| Observed error | What to check |
| --- | --- |
| Issuer unknown / certificate verification failed | Build: issuing CA and chain, certificate dates/name and clock. If company HTTPS inspection is used, pass its reviewed CA with `--ca-cert` or `NRPE_CA_CERT`. A supplied CA does not guarantee it is the right issuer. |
| Expired certificate / hostname mismatch | Correct the certificate, endpoint or clock; adding an unrelated CA cannot fix these. |
| Image/frontend pull trust failure | Configure trust in Docker Desktop/Engine and BuildKit. The build's `--ca-cert` does not configure engine trust. |
| Proxy authentication / HTTP 407 | Proxy reachability and credentials for the affected component. A CA cannot fix proxy authentication. |
| DNS resolution failure | Name resolution on the host and inside the affected Docker component, including VPN/proxy configuration. |
| Missing or expired repository metadata | Actual suite/service pack, repository URL, access rights and clock. Do not disable signatures/validity or substitute another distribution. |
| Checksum, signature or pinned-input mismatch | Stop and investigate the reviewed source/key/hash. Do not replace hashes or bypass signatures to obtain a pass. |
| No space left | Host and Docker storage separately. Preview [local cleanup](local-cleanup.md); it does not prune BuildKit caches or delete current packages. |
| Connection refused | Intended address/port, listener, daemon startup logs and any firewall REJECT. The connection failed before TLS negotiation. |

## NRPE on a deployed SLES 12 SP3 host

For `Could not complete SSL handshake. 1`, compare both NRPE and OpenSSL versions,
TLS versions, shared authenticated ciphers and CA/server/client certificate
settings. The message alone does not prove that a CA is missing. NRPE 2.15's
legacy anonymous DH and NRPE 4.x certificate authentication are different modes.

`Receive header underflow` can also result from mismatched TLS modes/packet
versions or access rejection. Check `-2` for NRPE 2.x, `allowed_hosts`, TCP wrappers
and simultaneous server logs before attributing it to certificates.

The [anonymized SLES 12 SP3 diagnostic](sles12sp3-plaintext-diagnostic.md) records
the separate plaintext test, unsupported `-f` option, configuration permissions,
wrong-host bind error and cleanup. Plaintext is temporary test evidence, not a
production fix. Use the [authenticated TLS configuration](configuration-examples.md#hosts-tls-and-fixed-commands)
for the custom NRPE 4.1.1 build. Do not apply modern `ssl_*` directives or
`disable_syslog=0` to an NRPE 2.15 configuration.

Inspect the real service definition and process command before changing startup
options. A manually started daemon is not managed by systemd; a failed second
service start can simply mean its port/PID is already occupied. Do not launch
another instance or remove live locks to hide that condition.

## NRPE: Unable to read output

A successful NRPE connection does not prove that the requested local plugin is
installed. `NRPE: Unable to read output` means the daemon did not obtain usable
standard output from the configured command. Missing executables are one cause;
also inspect permissions, the command definition and errors written to stderr.

On the monitored host, find the relevant `command[...]` definitions in the main
configuration and its included files. Verify their actual executable paths and
run the same command as the service user. For these example paths on SLES:

```sh
ls -l /usr/lib/nagios/plugins/check_swap \
      /usr/lib/nagios/plugins/check_ntp_time
sudo -u nagios /usr/lib/nagios/plugins/check_swap -w 50% -c 20%
echo "Exitcode: $?"
sudo -u nagios /usr/lib/nagios/plugins/check_ntp_time \
  -H 192.0.2.30 -w 0.5 -c 2
echo "Exitcode: $?"
```

Replace the NTP address with a real reachable NTP server. These commands execute
checks on the monitored host; their plugin exit statuses distinguish monitoring
results from execution errors. Verify that the selected server provides NTP and
that the required UDP 123 traffic is allowed if the installed NTP plugin times out.

For SLES 12 SP3, search the configured matching repositories and install the
missing plugin packages if available:

```sh
zypper search -s monitoring-plugins-swap monitoring-plugins-ntp
sudo zypper install monitoring-plugins-swap monitoring-plugins-ntp
rpm -ql monitoring-plugins-swap monitoring-plugins-ntp
```

Use authorized SLES-12 repositories and retain repository signature checks.
The NRPE custom server and its `monitoring-plugins-nrpe` client package do not
supply every monitoring plugin. Confirm the installed paths rather than assuming
that another distribution uses the same directory. If the `command[...]` paths
need changing, edit them and restart `nrpe.service`; merely installing a missing
executable at an already configured path does not require an NRPE restart.

Example definitions matching the calls below:

```nrpe
command[check_swap]=/usr/lib/nagios/plugins/check_swap $ARG1$
command[check_ntp_time]=/usr/lib/nagios/plugins/check_ntp_time -H $ARG1$ -w $ARG2$ -c $ARG3$
```

From the monitoring host, using fictional target `192.0.2.20` and NTP server
`192.0.2.30`:

```sh
check_nrpe -H 192.0.2.20 -p 5666 -2 \
  -c check_swap -a '-w 50% -c 20%'
check_nrpe -H 192.0.2.20 -p 5666 -2 \
  -c check_ntp_time -a 192.0.2.30 0.5 2
```

Use the deployment's required client TLS/certificate options too. Do not add
`-n` when the daemon expects TLS. These definitions require deliberately enabled
runtime arguments for trusted clients; keep Bash substitution and NRPE's default
metacharacter protections intact. Prefer fixed commands when arguments are not
needed; see [configuration examples](configuration-examples.md).

The operator confirmed this missing-plugin cause and successful installation of
`monitoring-plugins-swap` and `monitoring-plugins-ntp` on a SLES 12 SP3 test host
on 2026-10-29. This is operator-reported evidence, not an automated lifecycle or
certificate-authentication test.

For the complete operator-reported journey, including the OS correction, old
plaintext diagnostic, client/server package confusion, firewall and final plugin
fix, read the [SLES field note](../website/content/sles12-handshake.md).

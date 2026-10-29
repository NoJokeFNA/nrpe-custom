# Service checks before TLS changes

**Field note · 28–29 October 2026 · SLES 12 SP3 · NRPE 2.15 → 4.1.1**

This account is based on the operator's reported commands and output during
troubleshooting. Hostnames and addresses are anonymized. It is an observation
from one deployment, not a recommendation to disable production TLS.

## The symptom

The daemon logged `Error: Could not complete SSL handshake. 1`. Checking
`/etc/os-release`, the installed RPM and linked libraries established the actual
platform: **SLES 12 SP3**, NRPE `2.15-4.24` and OpenSSL `1.0.2j-fips` with the
OpenSSL 1.0 ABI. This identity determined the native build target. Modern
configuration directives did not add certificate authentication support to the
existing NRPE 2.15 executable.

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

## The operator's later clarification: start the missing service

The operator later reported that the missing `nrpe.service` was the cause of
their non-working checks: starting it alongside `nagios.service` restored the
combined setup. A custom package was not needed to correct that service state.
See the [combined service and TLS FAQ](../../docs/faq.md#nrpe-checks-on-sles-services-first-then-ssltls)
for the service commands and the order of checks.

This updates the outcome of the account. It does not establish that every
previous handshake log entry came from a stopped daemon, or identify a cipher
or certificate fix. The earlier manual/plaintext tests and the eventual managed
service state are distinct observations. Confirm the current listener and
repeat the actual monitoring check before changing TLS policy.

## What the custom build adds when it is actually needed

The project now targets genuine SLES 12 SP3. Its NRPE 4.1.1 container checks cover
certificate-authenticated TLS 1.2 against the original OpenSSL ABI; a separate
modern OpenSSL client test also passed with server identity verification and a
required client certificate. Those are separate test environments, not proof of
installation on this operator's server.

See the [SLES TLS policy](../../docs/installation.md#sles-certificate-authenticated-tls)
and [validation limits](../../docs/practical-validation.md) before deployment.
Temporary plaintext instances must be stopped and the intended managed service
restored. The next stages happened on a separate SLES 12 SP3 test host.

## The first installation attempt updated the client, not the daemon

On 29 October, the operator's installation transcript showed
`monitoring-plugins-nrpe` 4.1.1 installed, while `rpm -q nrpe` still reported
`nrpe-2.15-4.24`. New `ssl_*` directives were therefore being read by the old
server, which reported unknown options. A modern client does not upgrade the
remote daemon, even when both packages are named after NRPE.

The archive contains separate roles:

| Package | Purpose |
| --- | --- |
| `nrpe` | Server executable `/usr/sbin/nrpe`, configuration and managed service |
| `system-user-nagios` | Real account-package dependency; an existing Unix account alone is not an RPM provider |
| `monitoring-plugins-nrpe` | Client executable `check_nrpe`, not the server or every monitoring plugin |

The corrected installation route uses the checksum-verified local **server RPM**
with RPM's upgrade operation, adding the companion user package when required.
It does not require uninstalling Nagios Core or first installing NRPE 2.15.
Existing configuration, includes, credentials and service overrides need backup
and deliberate migration. The [installation guide](../../docs/installation.md#sles-12-sp3)
contains the complete commands and [replacement procedure](../../docs/installation.md#replace-an-existing-distribution-installation).

The later test-host output confirmed executable version **4.1.1**, an active
`nrpe.service`, the foreground command `/usr/sbin/nrpe -c /etc/nrpe.cfg -f`,
and listeners on TCP 5666. This established that the newer daemon was running.
It did not yet establish connectivity from the monitoring host. The old manual
`mkdir /run/nrpe` workaround is not a reboot fix; the new packaged service
supplies runtime-directory integration, which still needs a real reboot test.

## A timeout turned out to be the SLES firewall

Both a normal NRPE query and an earlier plaintext query timed out. The source
route was correct, and packet capture on the target showed repeated inbound
TCP SYN packets without a SYN-ACK response. For anonymized example hosts:

```sh
# Monitoring host: confirm source route and TCP connectivity.
ip route get 192.0.2.20
nc -vz -w 3 192.0.2.20 5666

# SLES target: observe traffic while repeating the remote connection.
sudo tcpdump -ni any -nn 'tcp port 5666'
```

Inspection showed active SuSEfirewall2, an INPUT drop policy and only SSH
allowed in the external zone. The connection was blocked before any TLS
negotiation. The reported temporary diagnostic allowance was scoped to the
monitoring source, target and NRPE port:

```sh
sudo iptables -I INPUT 1 \
  -s 192.0.2.10/32 -d 192.0.2.20/32 \
  -p tcp --dport 5666 -j ACCEPT
```

This changes live filtering immediately but is not persistent. The operator
then reported that the remote query succeeded:

```sh
check_nrpe -H 192.0.2.20 -p 5666 -2
```

```text
NRPE v4.1.1
```

For the observed SuSEfirewall2 external-zone setup, the permanent configuration
was proposed as an entry in `/etc/sysconfig/SuSEfirewall2`:

```ini
FW_SERVICES_ACCEPT_EXT="192.0.2.10/32,tcp,5666"
```

Preserve any existing entries and use the actual monitoring address. Leave the
SSH setting intact. Applying the reviewed configuration with
`sudo systemctl restart SuSEfirewall2.service` replaces live rules, including the
temporary rule. The operator confirmed connectivity after the allowance, but
has not supplied a separate persistence/reboot result. Do not claim that the
permanent rule or a reboot was tested. If abandoning the temporary test before a
firewall reload, remove exactly that rule using the same arguments with `-D`
instead of `-I INPUT 1`; never flush the firewall.

## A leftover no-SSL option caused the next failure

The version query without `-n` worked, but a load check still contained `-n`,
left over from the old plaintext diagnostic. That produced:

```text
CHECK_NRPE: Receive header underflow - only -1 bytes received (4 expected).
```

The server expected TLS while this client invocation explicitly disabled it.
Removing `-n` made the load check work, as confirmed by the operator:

```sh
check_nrpe -H 192.0.2.20 -p 5666 -2 \
  -c check_load -a '12.0,10.0,7.0' '15.0,13.0,10.0'
```

These are the reported example thresholds, not sizing recommendations. The
server had deliberately enabled runtime command arguments. `-2` selects NRPE
packet version 2; it does not disable TLS. Remove a leftover `-n` from the
corresponding Nagios command definition too if it was added there.

A related observation was that a working Debian 12 configuration had all
`ssl_*` options commented out. Comments leave NRPE's built-in defaults in use;
they do not switch encryption off. The successful SLES version/load queries
showed SSL communication, but did not demonstrate certificate-authentication
policy, hostname verification or the negotiated cipher. They must not be
reported as a completed mutual-TLS validation.

## Swap and NTP needed their own plugin packages

Only Swap and NTP checks then failed with `NRPE: Unable to read output`. Their
argument definitions matched the client calls, but the configured executables
were absent from `/usr/lib/nagios/plugins`. NRPE had no local plugin to execute.

The operator installed the missing packages from matching repositories and
confirmed that both checks worked afterwards:

```sh
zypper search -s monitoring-plugins-swap monitoring-plugins-ntp
sudo zypper install monitoring-plugins-swap monitoring-plugins-ntp
rpm -ql monitoring-plugins-swap monitoring-plugins-ntp
```

NRPE supplies remote execution; it does not bundle every monitoring check.
Verify installed paths against `command[...]` and run plugins as `nagios` when
troubleshooting. Installing an executable at an already configured path alone
does not require restarting NRPE; changing its configuration does. The
[plugin troubleshooting guide](../../docs/troubleshooting.md#nrpe-unable-to-read-output)
includes the exact argument mapping, local tests and anonymized remote calls.

## Outcome and limits

The reported sequence reached a running NRPE 4.1.1 server and working remote
version, load, Swap and NTP checks. The final blockers on the test host were a
firewall drop, a leftover plaintext-client option and missing plugin packages.
They were separate problems, not evidence of one continuing SSL defect.

The earlier service-start clarification, old-daemon plaintext tests and later
custom-server test are different stages and hosts. This account does not
invent the missing package-transaction record, artifact checksums, certificate
verification evidence, reboot or rollback results. Those remain covered by the
[deployment checklist](../../docs/sles12sp3-deployment-checklist.md) and
[practical validation procedure](../../docs/practical-validation.md).

Check in order: actual OS and server package, managed service and listener,
network reachability, compatible TLS modes, then installed plugins and their
argument definitions. Change one layer at a time and repeat the same remote
check so each result has a clear meaning.

# SLES 12 SP3: isolating an NRPE TLS handshake failure

This procedure documents a user-performed diagnostic on **SLES 12 SP3** with
NRPE **2.15-4.24**, OpenSSL **1.0.2j-fips** and a monitoring host running
`check_nrpe` **4.1.0**. The original daemon reported
`Error: Could not complete SSL handshake. 1`. A separate plaintext test returned
`NRPE_PLAIN_OK`. Hostnames and addresses below are anonymized examples.

The test runs a second NRPE instance on TCP **15666**, with its own configuration
and PID file. The existing service on TCP **5666**, its configuration and Nagios
check definitions remain unchanged. No package installation, systemd override,
`daemon-reload` or production service restart is needed.

Plaintext is a temporary diagnostic, not a deployment recommendation: the test
has no TLS encryption or certificate authentication. Use a trusted network and
restrict access to the monitoring host. Stop the test instance afterwards.

## Example hosts and prerequisites

| Role | Example hostname | Example address |
| --- | --- | --- |
| Monitoring host with `check_nrpe` | `monitor01` | `192.0.2.10` |
| SLES 12 SP3 host with NRPE 2.15 | `sles-agent01` | `192.0.2.20` |

The addresses belong to a documentation range. **Replace them with your actual
addresses before running the commands.** `server_address` must be assigned to
the SLES host; `allowed_hosts` must contain the source address the monitoring
host actually uses. Check the hostname before working on either machine.

On the SLES host, inspect the platform and local addresses:

```sh
hostname
cat /etc/os-release
/usr/sbin/nrpe -V
ip -4 addr show
sudo ss -ltnp | grep ':15666'
```

Expect SLES `VERSION_ID="12.3"` and NRPE 2.15. An NRPE version/usage command
may exit nonzero after printing its output. Port 15666 must be unused; no output
from the final command is expected before starting the test. If a previous test
directory or instance exists, inspect and clean it up before reusing these paths.
Allow TCP 15666 only from the monitoring host if a firewall change is necessary;
record and later remove only that temporary rule.

## 1. Create the isolated configuration on the SLES host

NRPE 2.15 does **not** support the foreground option `-f`. Use its daemon option
`-d` with `-n` to disable TLS for this instance only. A modern `ssl_...` setting
in the configuration is not a substitute for that startup option.

```sh
sudo install -d -o root -g nagios -m 0750 /run/nrpe-plain-test
sudo install -d -o nagios -g nagios -m 0750 /run/nrpe-plain-test/runtime

sudo tee /run/nrpe-plain-test/nrpe.cfg >/dev/null <<'EOF'
server_address=192.0.2.20
server_port=15666
pid_file=/run/nrpe-plain-test/runtime/nrpe.pid
nrpe_user=nagios
nrpe_group=nagios
allowed_hosts=192.0.2.10
dont_blame_nrpe=0
command_timeout=10
connection_timeout=10
command[check_plain_test]=/usr/bin/printf 'NRPE_PLAIN_OK\n'
EOF

sudo chown root:nagios /run/nrpe-plain-test/nrpe.cfg
sudo chmod 0640 /run/nrpe-plain-test/nrpe.cfg
sudo -u nagios test -r /run/nrpe-plain-test/nrpe.cfg \
  && echo 'Test configuration is readable'
```

The root-owned configuration is readable by `nagios`; its runtime subdirectory
allows that account to write the separate PID file. Command arguments remain
disabled. The test defines only a fixed `printf` command, not production checks.

## 2. Start and inspect the test instance on the SLES host

```sh
sudo -u nagios /usr/sbin/nrpe \
  -c /run/nrpe-plain-test/nrpe.cfg -d -n

sudo ss -ltnp | grep ':15666'
```

With `-d`, the prompt returns because the daemon runs in the background. Confirm
that `ss` shows NRPE listening on the chosen local address and port 15666 before
testing remotely. A returned prompt alone does not establish successful startup.

For startup errors:

```sh
sudo journalctl -t nrpe --since '5 minutes ago' --no-pager
```

If you change this configuration later, stop **only the test instance** using
the PID procedure below, then repeat this start command. No systemd reload is
required for the separate daemon.

## 3. Run the check from the monitoring host

```sh
/usr/lib/nagios/plugins/check_nrpe \
  -H 192.0.2.20 -p 15666 -2 -n -c check_plain_test
```

Adjust the plugin path if needed. `-2` selects the packet format understood by
NRPE 2.15; `-n` selects plaintext, matching the test daemon. Do not modify global
Nagios command definitions or remove TLS from other hosts' checks.

Expected output:

```text
NRPE_PLAIN_OK
```

This is the result reported by the user for the original SLES 12 SP3 host. It
confirms reachability on the test port, access acceptance and execution of this
fixed command without TLS. It narrows the original problem toward TLS negotiation,
but does not identify a specific cipher/certificate cause, test the production
port or commands, or prove an upgrade has fixed the real deployment.

## Troubleshooting encountered during this procedure

| Symptom | Meaning and next step |
| --- | --- |
| `invalid option -- 'f'` | NRPE 2.15 lacks `-f`; start this test with `-d -n`. |
| `Unable to open config file ... for reading` | Check the file's `root:nagios` ownership, `0640` mode and directory traversal permissions. `chmod 0640` alone leaves a root-group file unreadable to `nagios`. |
| `Cannot assign requested address` | The configured address is not local to this host. Check `hostname` and `ip -4 addr show`; make sure you are on the intended SLES server. |
| `Connection refused` | Check for a listener with `ss` and inspect startup logs; also consider an actively rejecting firewall. This happens before NRPE/TLS negotiation. |
| `Receive header underflow` | Not a specific TLS diagnosis. Confirm both ends use `-n`, the client uses `-2`, and the address/port are correct; inspect server logs, `allowed_hosts` and any TCP-wrapper rules. |
| Timeout | Check routing, firewall policy and the actual listening address. Do not disable the firewall globally. |
| `rmdir: Directory not empty` | The `runtime` subdirectory or PID file remains. Stop the test and remove those specific paths in the order below. |

The old daemon also reported `disable_syslog=0` as an unknown configuration
option in the original production configuration. That is separate from the
TLS failure; this minimal test configuration intentionally omits that directive.

## 4. Stop the test and remove its files on the SLES host

Inspect the PID and command first. It must refer to the separate instance using
`/run/nrpe-plain-test/nrpe.cfg`, not the production NRPE daemon:

```sh
sudo ps -p "$(sudo cat /run/nrpe-plain-test/runtime/nrpe.pid)" \
  -o pid,user,args
```

After confirming that identity, stop that process:

```sh
sudo kill "$(sudo cat /run/nrpe-plain-test/runtime/nrpe.pid)"
sudo ss -ltnp | grep ':15666'
```

Wait until port 15666 has no listener. If the PID file is missing or stale, use
`ss` and process inspection to identify the test process; do not use `killall
nrpe`, stop the production service, or send a signal to an unverified PID.

Then remove the specific test files and directories:

```sh
sudo rm -f /run/nrpe-plain-test/runtime/nrpe.pid
sudo rm /run/nrpe-plain-test/nrpe.cfg
sudo rmdir /run/nrpe-plain-test/runtime
sudo rmdir /run/nrpe-plain-test
```

Remove any firewall exception added specifically for this diagnostic. Existing
production files and the listener on port 5666 are unaffected. The test paths
under `/run` are temporary and do not survive reboot.

For the certificate-authenticated upgrade path, see the
[SLES 12 SP3 build guide](sles12sp3.md#tls-and-the-original-handshake-failure)
and [SLES TLS configuration example](configuration-examples.md#hosts-tls-and-fixed-commands).
The project's NRPE 4.1.1 container tests are separate evidence from this
user-performed plaintext diagnostic.

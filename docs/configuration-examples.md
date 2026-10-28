# NRPE configuration examples

These fragments illustrate a restricted deployment; they are not complete
configuration files. Merge reviewed settings into `/etc/nagios/nrpe.cfg` on
Debian or `/etc/nrpe.cfg` on SLES. Follow the [official NRPE manuals](https://github.com/NagiosEnterprises/nrpe)
for server/client setup, plugin installation and TLS provisioning. Never copy
the project's test CA into production trust stores.

## Hosts, TLS and fixed commands

Example server settings, replacing the documentation IP and all certificate paths:

```ini
allowed_hosts=127.0.0.1,::1,192.0.2.10
dont_blame_nrpe=0
allow_bash_command_substitution=0
ssl_version=TLSv1.2+
ssl_use_adh=0
ssl_client_certs=2
ssl_cacert_file=/etc/nrpe-tls/monitoring-ca.pem
ssl_cert_file=/etc/nrpe-tls/server.pem
ssl_privatekey_file=/etc/nrpe-tls/server.key
```

For this project's **SLES 12 SP3 NRPE 4.1.1** build with RSA certificates,
replace the `ssl_version` and `ssl_use_adh` settings above with all three lines:

```ini
ssl_version=TLSv1.2
ssl_use_adh=1
ssl_cipher_list=DHE-RSA-AES256-GCM-SHA384:!aNULL:!eNULL
```

Keep the CA, server key/certificate and mandatory client-certificate settings.
On this NRPE/OpenSSL combination, `ssl_use_adh=0` also skips initialization of
certificate-authenticated finite-field DH. The explicit cipher list permits
only authenticated DHE-RSA with AES-256-GCM and excludes anonymous and null
ciphers even though the initialization switch is enabled. This policy passed
with 2048-bit DH and an OpenSSL 3.5.7 client using its default security level,
server hostname/chain verification and a separate client certificate. Missing
client certificates were rejected. Do not use `ssl_use_adh=1` without the
restrictive cipher list, and confirm that the actual monitoring client supports
the chosen suite. These options do not apply to the old NRPE 2.15 daemon.

The server certificate needs an appropriate identity and certificate chain. Give
the NRPE service account the permissions necessary to read its key, without
making that key readable by other users. Restrict incoming TCP 5666 to the actual
monitoring hosts. Client-certificate verification and IP allowlisting have
different roles; configure both. Do not reduce TLS settings to make an
unconfigured client connect.

Prefer fixed command definitions when caller-supplied arguments are unnecessary:

```ini
command[check_load_standard]=/usr/lib/nagios/plugins/check_load -w 5,4,3 -c 10,8,6
command[check_load_busy]=/usr/lib/nagios/plugins/check_load -w 10,8,6 -c 20,16,12
```

These are illustrative thresholds, not capacity recommendations. Install your
distribution's `check_load` plugin separately and locate its actual executable;
SLES may use a different plugin directory. NRPE does not install every monitoring
plugin. Keep command definitions and plugin/wrapper files owned by an administrator
and unwritable by the NRPE account.

From the monitoring host, a fixed check can be requested without `-a`:

```sh
check_nrpe -H nrpe.example.internal -d 0 \
  -A /etc/monitoring/tls/monitoring-ca.pem \
  -C /etc/monitoring/tls/client.pem \
  -K /etc/monitoring/tls/client.key \
  -c check_load_standard
```

Use your client's actual paths and the certificate-name verification options
supported by its version. A successful encrypted connection alone does not
establish that the intended peer identity is verified.

## Optional named argument profiles

Enable this only for trusted authenticated monitoring clients when distinct
fixed command names are unsuitable. NRPE substitutes `$ARGn$` into a command
before invoking its shell: a wrapper's argument validation happens **after**
that substitution and is not, by itself, protection against shell injection.
Preserve NRPE's default forbidden-metacharacter checks (including single quotes,
backticks, backslashes, semicolons and newlines) and keep Bash substitution
disabled. Do not loosen `nasty_metachars`, put untrusted text in command definitions,
or expose this interface to arbitrary callers.

The [example wrapper](../examples/check-load-profile.sh) accepts only `standard`
or `busy` and maps them to fixed plugin options. Its first argument is an absolute
plugin path fixed by the administrator in the server configuration; the caller
does not select that path. It does not use `eval`, run a shell on received strings,
or accept arbitrary plugin options. Install it after reviewing it:

```sh
sudo install -d -o root -g root -m 0755 /usr/local/libexec/nrpe-custom
sudo install -o root -g root -m 0755 examples/check-load-profile.sh \
  /usr/local/libexec/nrpe-custom/check-load-profile
```

Copy the reviewed example onto the destination first; that command assumes an
`examples/` directory in the current location. Test the locally installed wrapper
as the service account with the actual plugin path before exposing it through NRPE.

Example definition, using the Debian plugin path:

```ini
dont_blame_nrpe=1
allow_bash_command_substitution=0
command[check_load_profile]=/usr/local/libexec/nrpe-custom/check-load-profile /usr/lib/nagios/plugins/check_load '$ARG1$'
```

Then request `-c check_load_profile -a standard` using the same client TLS options
as above. Requesting `unknown` should return NRPE status `UNKNOWN` (3), without
running the plugin. The wrapper preserves the plugin's OK/WARNING/CRITICAL exit
status for accepted profiles. Additional wrapper arguments are rejected; do not
add extra `$ARGn$` placeholders to the definition.

The unit tests exercise profile mapping, plugin exit status, and rejection of
unknown/malformed arguments. They do not prove that a deployed NRPE configuration
keeps its pre-shell protections intact. Test rejection of forbidden characters
and unknown profiles in an isolated deployment before production use, and do
not send destructive injection probes to production hosts.

During introduction, both profiles, unknown-profile rejection and NRPE's
pre-shell metacharacter rejection were also exercised over real TLS in a
disposable Debian 12 container with the installed custom server. A fake load
plugin recorded the exact options, so that check validates argument mapping and
rejection, not the real plugin's load measurements or production capacity limits.

Restart the relevant service after reviewing the configuration and verify checks
from the real monitoring host. See [installation](installation.md),
[updates and rollback](updates-and-rollback.md), and [security](security.md).

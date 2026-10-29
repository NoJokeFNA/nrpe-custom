# Verify NRPE transport and certificate authentication

A successful encrypted NRPE query is useful evidence, but does not by itself
prove certificate or hostname verification. Run these checks from the actual
monitoring host, in order. Use test credentials and an isolated target for
negative tests. Follow the [installation guide](installation.md) and
[upstream manuals](https://github.com/NagiosEnterprises/nrpe) for provisioning.

Examples use fictional target `192.0.2.20`, monitoring host `192.0.2.10` and
certificate name `nrpe.example.internal`. Replace these and all file paths.
The OpenSSL examples require a modern monitoring-client OpenSSL with
`-verify_hostname` and `-verify_return_error` support; check its local help.
Do not replace the SLES target's system OpenSSL to run client-side diagnostics.

## 1. Establish the actual server and TCP path

On the monitored host, run the read-only
[server diagnostic](troubleshooting.md#read-only-target-server-inspection).
Confirm daemon version/package, intended managed service, configuration and
listener. On the monitoring host:

```sh
ip route get 192.0.2.20
nc -vz -w 3 192.0.2.20 5666
```

Expected: the route selects the intended monitoring source and TCP connects.
If it times out, inspect the target's listener, simultaneous packet capture and
firewall. Repeated inbound SYN packets without SYN-ACK are not a TLS handshake.
A failed TCP check cannot be repaired by adding a CA or changing ciphers.

## 2. Distinguish encryption from authentication

```sh
check_nrpe -H 192.0.2.20 -p 5666 -2
```

Without `-n`, the client attempts SSL/TLS. A returned `NRPE v4.1.1` demonstrates
a completed encrypted NRPE exchange with that running endpoint. Record the
actual version returned. `-2` selects packet format, not plaintext. A client
using `-n` against a TLS daemon can produce `Receive header underflow`.

Commented `ssl_*` settings mean daemon defaults apply, not that TLS is disabled.
Read included configuration files too. A successful default-mode query does not
prove CA trust, the intended server identity or mandatory client certificates.
If the server requires certificates, supply its intended client options rather
than weakening that policy to make this simple example succeed.

## 3. Verify the server's chain and identity explicitly

For the documented SLES 12 SP3/NRPE 4.1.1 policy, provision the
[complete authenticated TLS configuration](installation.md#sles-certificate-authenticated-tls)
first. On a modern monitoring host:

```sh
openssl s_client -connect 192.0.2.20:5666 \
  -servername nrpe.example.internal \
  -verify_hostname nrpe.example.internal -verify_return_error \
  -CAfile /etc/monitoring/tls/monitoring-ca.pem \
  -cert /etc/monitoring/tls/client.pem \
  -key /etc/monitoring/tls/client.key \
  -tls1_2 -cipher 'DHE-RSA-AES256-GCM-SHA384:!aNULL:!eNULL' \
  </dev/null
printf 'OpenSSL exit status: %s\n' "$?"
```

Expected: successful chain/name verification, TLS 1.2 and the intended
authenticated cipher. Require a successful verification result and inspect the
complete output, not just a displayed certificate. These protocol/cipher options
are specific to the documented SLES policy, not a universal configuration for
all targets. Do not ignore a nonzero verification result or treat a displayed
certificate as proof that verification succeeded.

This is a TLS diagnostic, not an NRPE request: no valid NRPE packet is sent after
the handshake. The daemon can log a later packet/read error when the diagnostic
disconnects. An OpenSSL EOF/connection-close failure is not a passing full
application test; distinguish certificate/handshake evidence from that close.
Record this separately from the real check below.

## 4. Require rejection of invalid credentials on a test target

After the positive test, repeat against the **same target and port**:

| Change | Expected result |
| --- | --- |
| Use a wrong expected hostname with `-verify_hostname` | Server identity verification fails |
| Use a different, valid but unrelated test CA file | Server chain verification fails |
| Omit `-cert` and `-key` while server `ssl_client_certs=2` | Server rejects the client for missing credentials |
| Present a client certificate from an untrusted test CA | Server rejects the client certificate |

Confirm rejection in simultaneous daemon/client logs. A timeout or TCP failure
is not proof that certificate enforcement worked. Do not weaken the server to
make a negative test pass; restore the original intended client options after
each test. Keep private keys and certificate contents out of published evidence.

## 5. Execute a real permitted NRPE check

For the same SLES policy, with a configured fixed command:

```sh
check_nrpe -H 192.0.2.20 -p 5666 -2 -d 0 -S TLSv1.2 \
  -L 'DHE-RSA-AES256-GCM-SHA384:!aNULL:!eNULL' \
  -A /etc/monitoring/tls/monitoring-ca.pem \
  -C /etc/monitoring/tls/client.pem \
  -K /etc/monitoring/tls/client.key \
  -c check_load_standard
```

Verify the plugin exists and runs as the service user. Compare its expected
output/status with the remote result. NRPE plugin status 1/2/3 can represent
WARNING/CRITICAL/UNKNOWN rather than a transport failure.

Do not assume `check_nrpe -A` implements hostname verification: verify the exact
client version's behavior and available options. An independent OpenSSL hostname
test does not add that behavior to future Nagios checks. Record what each client
actually verifies and provision credentials/access controls accordingly.

## Evidence to retain

Record daemon/client/OpenSSL versions, exact package identity, sanitized command,
negotiated protocol/cipher, verification outcomes and application output/status.
Keep four distinct results: TCP reachability, encrypted NRPE exchange, server
chain/name verification and client-certificate enforcement. None substitutes for
[reboot, update and rollback validation](deployment-validation-template.md).
Build-time `--ca-cert` configures repository HTTPS, not deployed NRPE credentials.

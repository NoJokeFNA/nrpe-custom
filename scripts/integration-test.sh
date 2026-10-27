#!/usr/bin/env bash
set -Eeuo pipefail

: "${DEBIAN_CODENAME:?Set DEBIAN_CODENAME via Compose}"
actual_codename="$(. /etc/os-release; printf '%s' "$VERSION_CODENAME")"
[[ "$actual_codename" == "$DEBIAN_CODENAME" ]] || {
  echo "ERROR: Expected ${DEBIAN_CODENAME}, running ${actual_codename}" >&2; exit 1;
}
[[ "$(dpkg --print-architecture)" == amd64 ]] || {
  echo 'ERROR: Integration tests require amd64' >&2; exit 1;
}

shopt -s nullglob
packages=(/packages/nagios-nrpe-server_*_amd64.deb)
(( ${#packages[@]} == 1 )) || {
  echo 'ERROR: Expected exactly one server package. Build this target first.' >&2; exit 1;
}
package="${packages[0]}"
cd /packages
sha256sum --check SHA256SUMS
grep -Fx -- "$(sha256sum "${package##*/}")" SHA256SUMS > /dev/null
[[ "$(dpkg-deb --field "$package" Package)" == nagios-nrpe-server ]]
[[ "$(dpkg-deb --field "$package" Architecture)" == amd64 ]]
version="$(dpkg-deb --field "$package" Version)"
[[ "$version" =~ \+withargs[0-9]+$ ]] || {
  echo "ERROR: Not a custom package version: $version" >&2; exit 1;
}

apt-get update
apt-get install -y --no-install-recommends "$package"
[[ "$(dpkg-query -W -f='${Version}' nagios-nrpe-server)" == "$version" ]]
grep -Eq '^[[:space:]]*dont_blame_nrpe=0[[:space:]]*$' /etc/nagios/nrpe.cfg || {
  echo 'ERROR: Installed package does not keep argument handling disabled by default' >&2; exit 1;
}
if grep -Eq '^[[:space:]]*dont_blame_nrpe=1[[:space:]]*$' /etc/nagios/nrpe.cfg; then
  echo 'ERROR: Installed package enables argument handling by default' >&2; exit 1
fi
echo "PASS: Installed nagios-nrpe-server $version with arguments disabled by default"

runtime="$(mktemp -d /tmp/nrpe-integration.XXXXXXXX)"
server_pid=''
stop_server() {
  if [[ -n "$server_pid" ]]; then
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
    server_pid=''
  fi
}
cleanup() {
  result=$?
  trap - EXIT
  stop_server
  if (( result != 0 )); then
    cat "$runtime"/*.log >&2 2>/dev/null || true
  fi
  rm -rf "$runtime"
  exit "$result"
}
trap cleanup EXIT

# Use a short-lived test certificate for both ends of the local TLS connection.
openssl req -x509 -newkey rsa:2048 -nodes -days 1 \
  -subj '/CN=localhost' -keyout "$runtime/key.pem" \
  -out "$runtime/cert.pem" > "$runtime/certificate.log" 2>&1
cat > "$runtime/nrpe.cfg" <<EOF
log_file=$runtime/nrpe.log
pid_file=$runtime/nrpe.pid
server_address=127.0.0.1
server_port=5666
nrpe_user=nagios
nrpe_group=nagios
allowed_hosts=127.0.0.1
dont_blame_nrpe=0
allow_bash_command_substitution=0
ssl_cert_file=$runtime/cert.pem
ssl_privatekey_file=$runtime/key.pem
ssl_cacert_file=$runtime/cert.pem
ssl_client_certs=2
ssl_use_adh=0
ssl_version=TLSv1.2+
command_timeout=10
connection_timeout=10
command[check_ready]=/usr/bin/printf 'NRPE_READY\n'
command[check_args]=/usr/bin/printf 'NRPE_ARGS:%s:%s\n' '\$ARG1\$' '\$ARG2\$'
EOF
touch "$runtime/nrpe.log" "$runtime/server.log" "$runtime/client.log"
chown -R nagios:nagios "$runtime"
chmod 700 "$runtime"
chmod 600 "$runtime/key.pem"

client=(/usr/lib/nagios/plugins/check_nrpe -H 127.0.0.1 -t 5 -d 0
  -A "$runtime/cert.pem" -C "$runtime/cert.pem" -K "$runtime/key.pem")
start_server() {
  /usr/sbin/nrpe -f -c "$runtime/nrpe.cfg" >> "$runtime/server.log" 2>&1 &
  server_pid=$!
  for (( attempt=0; attempt<30; attempt++ )); do
    kill -0 "$server_pid" 2>/dev/null || {
      echo 'ERROR: NRPE exited during startup' >&2; return 1;
    }
    if reply="$("${client[@]}" -c check_ready 2>> "$runtime/client.log")" \
      && [[ "$reply" == NRPE_READY ]]; then
      return 0
    fi
    sleep 1
  done
  echo 'ERROR: NRPE did not become ready' >&2
  return 1
}

start_server
if reply="$("${client[@]}" -c check_args -a alpha beta 2>> "$runtime/client.log")"; then
  echo "ERROR: Arguments were accepted while disabled: $reply" >&2; exit 1
fi
# A second control request rules out a dead server as the reason for rejection.
[[ "$("${client[@]}" -c check_ready)" == NRPE_READY ]]
echo 'PASS: Running NRPE rejects arguments while dont_blame_nrpe=0'
stop_server

# Change only the disposable test configuration, never the packaged default.
sed -i 's/^dont_blame_nrpe=0$/dont_blame_nrpe=1/' "$runtime/nrpe.cfg"
start_server
echo 'Testing with dont_blame_nrpe=1: forwarding two different argument pairs'
reply="$("${client[@]}" -c check_args -a alpha beta)"
[[ "$reply" == NRPE_ARGS:alpha:beta ]] || {
  echo "ERROR: Unexpected argument response: $reply" >&2; exit 1;
}
reply="$("${client[@]}" -c check_args -a gamma delta)"
[[ "$reply" == NRPE_ARGS:gamma:delta ]] || {
  echo "ERROR: Arguments did not reach the check correctly: $reply" >&2; exit 1;
}
echo 'PASS: Arguments enabled (dont_blame_nrpe=1); check_nrpe receives alpha/beta and gamma/delta over TLS'
echo "PASS: Integration test completed for ${DEBIAN_CODENAME} ($version)"

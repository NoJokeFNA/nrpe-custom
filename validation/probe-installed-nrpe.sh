#!/bin/sh
# Research harness for already installed packages in disposable Linux containers.
# No package installation, host port publication or production configuration changes.
set -eu
if [ "${NRPE_DISPOSABLE_PROBE:-}" != 1 ] || { [ ! -f /.dockerenv ] && [ ! -f /run/.containerenv ]; }; then
 echo 'Refusing: this probe requires an explicitly marked disposable container' >&2
 exit 2
fi
[ "$(id -u)" = 0 ] || { echo 'Run as container root to use the package-provided account' >&2; exit 2; }
nrpe=$(command -v nrpe || true)
[ -n "$nrpe" ] || nrpe=/usr/sbin/nrpe
client=''
for path in /usr/lib/nagios/plugins/check_nrpe /usr/lib64/nagios/plugins/check_nrpe /usr/lib/monitoring-plugins/check_nrpe; do
 if [ -x "$path" ]; then client=$path; break; fi
done
[ -x "$nrpe" ] && [ -n "$client" ] || { echo 'NRPE executables unavailable' >&2; exit 1; }
"$nrpe" -V || true
"$client" -V || true
sha256sum "$nrpe" "$client"
service_user=''
for candidate in nrpe nagios; do
 if id "$candidate" >/dev/null 2>&1; then service_user=$candidate; break; fi
done
[ -n "$service_user" ] || { echo 'Real package-provided service account unavailable' >&2; exit 1; }
service_group=$(id -gn "$service_user")
probe_root=$(mktemp -d /tmp/nrpe-package-probe.XXXXXX)
chmod 0755 "$probe_root"
mkdir "$probe_root/runtime"
chown "$service_user:$service_group" "$probe_root/runtime"
pid=''
stop_daemon() {
 if [ -n "$pid" ]; then kill "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true; pid=''; fi
}
trap 'stop_daemon; rm -rf "$probe_root"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
for policy in 0 1; do
 cat > "$probe_root/nrpe.cfg" <<CFG
server_address=127.0.0.1
server_port=15666
allowed_hosts=127.0.0.1
nrpe_user=$service_user
nrpe_group=$service_group
pid_file=$probe_root/runtime/nrpe.pid
dont_blame_nrpe=$policy
allow_bash_command_substitution=0
connection_timeout=5
command_timeout=5
CFG
 cat >> "$probe_root/nrpe.cfg" <<'CFG'
command[check_baseline]=/bin/echo NRPE_BASELINE_OK
command[check_args]=/bin/echo NRPE_ARG_PROBE:$ARG1$:$ARG2$
CFG
 "$nrpe" -c "$probe_root/nrpe.cfg" -f -n > "$probe_root/daemon.log" 2>&1 &
 pid=$!
 ready=0
 for attempt in 1 2 3 4 5 6 7 8 9 10; do
  kill -0 "$pid" 2>/dev/null || { echo 'Daemon exited before baseline' >&2; cat "$probe_root/daemon.log"; exit 1; }
  baseline=$("$client" -H 127.0.0.1 -p 15666 -2 -n -t 3 -c check_baseline 2>&1 || true)
  if [ "$baseline" = NRPE_BASELINE_OK ]; then ready=1; break; fi
  sleep 0.2
 done
 [ "$ready" = 1 ] || { echo "BASELINE_FAILED=$baseline"; cat "$probe_root/daemon.log"; exit 1; }
 printf 'BASELINE_POLICY_%s=passed\n' "$policy"
 set +e
 output=$("$client" -H 127.0.0.1 -p 15666 -2 -n -t 3 -c check_args -a ALPHA BETA 2>&1)
 status=$?
 set -e
 printf 'ARGUMENT_POLICY_%s_EXIT=%s\nARGUMENT_POLICY_%s_OUTPUT=%s\n' "$policy" "$status" "$policy" "$output"
 if [ "$policy" = 0 ] && [ "$output" = NRPE_ARG_PROBE:ALPHA:BETA ]; then
  echo 'FAIL: arguments accepted while runtime policy disabled' >&2; exit 1
 fi
 if [ "$policy" = 1 ]; then
  if [ "$status" = 0 ] && [ "$output" = NRPE_ARG_PROBE:ALPHA:BETA ]; then echo 'ARGUMENT_CAPABILITY=confirmed'
  else echo 'ARGUMENT_CAPABILITY=not_demonstrated'; fi
 fi
 stop_daemon
done
echo 'SCOPE=disposable container; plaintext loopback; no TLS/systemd/reboot/upgrade claim'

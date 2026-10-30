#!/bin/sh
# Research harness for already installed packages in disposable Linux containers.
# No package installation, host port publication or production configuration changes.
set -eu
if [ "${NRPE_DISPOSABLE_PROBE:-}" != 1 ] || { [ ! -f /.dockerenv ] && [ ! -f /run/.containerenv ]; }; then
 echo 'Refusing: this probe requires an explicitly marked disposable container' >&2
 exit 2
fi
[ "$(id -u)" = 0 ] || { echo 'Run as container root to use the package-provided account' >&2; exit 2; }
nrpe=${NRPE_PROBE_SERVER:-$(command -v nrpe || true)}
[ -n "$nrpe" ] || nrpe=/usr/sbin/nrpe
client=${NRPE_PROBE_CLIENT:-}
for path in /usr/lib/nagios/plugins/check_nrpe /usr/lib64/nagios/plugins/check_nrpe /usr/lib/monitoring-plugins/check_nrpe; do
 if [ -z "$client" ] && [ -x "$path" ]; then client=$path; break; fi
done
[ -x "$nrpe" ] && [ -x "$client" ] || { echo 'NRPE executables unavailable' >&2; exit 1; }
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
transport=${NRPE_PROBE_TRANSPORT:-plain}
case "$transport" in plain|tls) ;; *) echo 'Use plain or tls transport' >&2; rm -rf "$probe_root"; exit 2 ;; esac
pid=''
stop_daemon() {
 if [ -n "$pid" ]; then kill "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true; pid=''; fi
}
trap 'stop_daemon; rm -rf "$probe_root"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
if [ "$transport" = tls ]; then
 command -v openssl >/dev/null
 for identity in trusted unrelated; do
  openssl req -x509 -newkey rsa:2048 -nodes -days 1 -subj "/CN=nrpe-probe-$identity" \
   -keyout "$probe_root/$identity.key" -out "$probe_root/$identity.pem" > "$probe_root/$identity.log" 2>&1
  chmod 0600 "$probe_root/$identity.key"
 done
 chown "$service_user:$service_group" "$probe_root/trusted.key"
fi
request() {
 if [ "$transport" = tls ]; then
  "$client" -H 127.0.0.1 -p 15666 -2 -t 3 -S TLSv1.2 -d 0 \
   -A "$probe_root/trusted.pem" -C "$probe_root/trusted.pem" -K "$probe_root/trusted.key" "$@"
 else
  "$client" -H 127.0.0.1 -p 15666 -2 -t 3 -n "$@"
 fi
}
for policy in 0 1; do
 cat > "$probe_root/nrpe.cfg" <<CFG
server_address=127.0.0.1
server_port=15666
allowed_hosts=127.0.0.1
nrpe_user=$service_user
nrpe_group=$service_group
pid_file=$probe_root/runtime/nrpe.pid
log_file=$probe_root/runtime/nrpe.log
dont_blame_nrpe=$policy
allow_bash_command_substitution=0
connection_timeout=5
command_timeout=5
CFG
 cat >> "$probe_root/nrpe.cfg" <<'CFG'
command[check_baseline]=/bin/echo NRPE_BASELINE_OK
command[check_args]=/bin/echo NRPE_ARG_PROBE:$ARG1$:$ARG2$
CFG
 if [ "$transport" = tls ]; then
  cat >> "$probe_root/nrpe.cfg" <<CFG
ssl_logging=0xff
ssl_version=TLSv1.2
ssl_use_adh=1
ssl_cipher_list=ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:!aNULL:!eNULL
ssl_cert_file=$probe_root/trusted.pem
ssl_privatekey_file=$probe_root/trusted.key
ssl_cacert_file=$probe_root/trusted.pem
ssl_client_certs=2
CFG
  set --
 else
  set -- -n
 fi
 "$nrpe" -c "$probe_root/nrpe.cfg" -f "$@" > "$probe_root/daemon.log" 2>&1 &
 pid=$!
 ready=0
 for attempt in 1 2 3 4 5 6 7 8 9 10; do
  kill -0 "$pid" 2>/dev/null || { echo 'Daemon exited before baseline' >&2; cat "$probe_root/daemon.log"; cat "$probe_root/runtime/nrpe.log" 2>/dev/null || true; exit 1; }
  baseline=$(request -c check_baseline 2>&1 || true)
  if [ "$baseline" = NRPE_BASELINE_OK ]; then ready=1; break; fi
  sleep 0.2
 done
 [ "$ready" = 1 ] || { echo "BASELINE_FAILED=$baseline"; cat "$probe_root/daemon.log"; cat "$probe_root/runtime/nrpe.log" 2>/dev/null || true; exit 1; }
 printf 'BASELINE_POLICY_%s=passed\n' "$policy"
 set +e
 output=$(request -c check_args -a ALPHA BETA 2>&1)
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
 if [ "$transport" = tls ] && [ "$policy" = 1 ]; then
  for negative in wrong_ca missing_client_cert; do
   if [ "$negative" = wrong_ca ]; then
    set -- -A "$probe_root/unrelated.pem" -C "$probe_root/trusted.pem" -K "$probe_root/trusted.key"
   else
    set -- -A "$probe_root/trusted.pem"
   fi
   if "$client" -H 127.0.0.1 -p 15666 -2 -t 3 -S TLSv1.2 -d 0 "$@" -c check_baseline > "$probe_root/negative.log" 2>&1; then
    echo "FAIL: TLS negative control accepted: $negative" >&2; exit 1
   fi
   printf 'TLS_NEGATIVE_%s=rejected\n' "$negative"
  done
  [ "$(request -c check_baseline)" = NRPE_BASELINE_OK ]
  echo 'TLS_AUTHENTICATED_BASELINE=passed'
 fi
 stop_daemon
done
printf 'TRANSPORT=%s\n' "$transport"
echo 'SCOPE=disposable IPv4 loopback; no hostname/service-manager/reboot/upgrade claim'

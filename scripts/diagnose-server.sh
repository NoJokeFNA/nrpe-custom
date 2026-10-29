#!/usr/bin/env bash
# Read-only inventory: never source NRPE configuration or execute its commands.
set -euo pipefail
export LC_ALL=C
config=''
unit=''
nrpe='/usr/sbin/nrpe'
monitor_ip=''
failures=0
warnings=0
usage() {
  cat <<'HELP'
Usage: bash scripts/diagnose-server.sh [--config PATH] [--unit UNIT]
       [--nrpe PATH] [--monitor-ip ADDRESS]
Read-only local NRPE checks. No installs, restarts, firewall changes or plugin execution.
Exit: 0 = no failed checks (review warnings), 1 = failed checks, 2 = invalid usage.
HELP
}
while (($#)); do
  case "$1" in
    --help|-h) usage; exit 0 ;;
    --config|--unit|--nrpe|--monitor-ip)
      if (($# < 2)) || [[ -z "$2" ]]; then usage >&2; exit 2; fi
      case "$1" in
        --config) config=$2 ;;
        --unit) unit=$2 ;;
        --nrpe) nrpe=$2 ;;
        --monitor-ip) monitor_ip=$2 ;;
      esac
      shift 2 ;;
    *) usage >&2; exit 2 ;;
  esac
done
if [[ "$nrpe" != /* || ( -n "$unit" && ! "$unit" =~ ^[A-Za-z0-9_.@-]+$ ) || "$unit" == -* ]]; then
  printf 'ERROR: use an absolute NRPE executable path and a plain service name.\n' >&2
  exit 2
fi
report() { printf '%s: %s\n' "$1" "$2"; }
fail() { failures=$((failures + 1)); report FAIL "$1"; }
warn() { warnings=$((warnings + 1)); report WARN "$1"; }
# Do not source even os-release: print only its well-known identity fields.
if [[ -r /etc/os-release ]]; then
  awk -F= '/^(NAME|VERSION_ID|ID)=/{print "OS: " $0}' /etc/os-release
fi
if [[ -z "$config" ]]; then
  if [[ -e /etc/nrpe.cfg ]]; then config=/etc/nrpe.cfg
  else config=/etc/nagios/nrpe.cfg; fi
fi
if [[ -z "$unit" ]]; then
  if [[ "$config" == /etc/nrpe.cfg ]]; then unit=nrpe.service
  else unit=nagios-nrpe-server.service; fi
fi
printf 'CONFIG: %s\nUNIT: %s\n' "$config" "$unit"
if [[ -x "$nrpe" ]]; then
  # Some NRPE versions print valid version information but exit nonzero.
  version=$("$nrpe" -V 2>&1 || true)
  if printf '%s\n' "$version" | awk '/^Version:/{print "NRPE " $0; found=1} END{exit !found}'; then
    report INFO 'Executable version is not the check_nrpe client version.'
  else fail 'The selected executable did not report an NRPE version.'; fi
else fail "NRPE executable missing or not executable: $nrpe"; fi
if command -v rpm >/dev/null 2>&1; then
  rpm -qf "$nrpe" 2>/dev/null || warn 'No RPM owns the selected executable.'
elif command -v dpkg-query >/dev/null 2>&1; then
  dpkg-query -S "$nrpe" 2>/dev/null || warn 'No Debian package owns the selected executable.'
else warn 'No supported package-query tool available.'; fi
service_user=''
if command -v systemctl >/dev/null 2>&1; then
  if systemctl is-active --quiet "$unit"; then report PASS 'Managed service is active.'
  else fail 'Managed service is not active or its state cannot be read.'; fi
  if systemctl is-enabled --quiet "$unit"; then report PASS 'Service is enabled for startup.'
  else warn 'Service is not enabled or its startup state cannot be read.'; fi
  service_user=$(systemctl show "$unit" -p User --value 2>/dev/null || true)
  # --value is unavailable on some older systemd releases.
  if [[ -z "$service_user" ]]; then
    service_user=$(systemctl show "$unit" -p User 2>/dev/null | sed -n 's/^User=//p' || true)
  fi
fi
if [[ -z "$service_user" ]]; then warn 'Cannot establish the service account from systemd.'
else printf 'SERVICE USER: %s\n' "$service_user"; fi
if command -v ss >/dev/null 2>&1; then
  report INFO 'Local TCP listeners (a listener alone does not prove remote reachability):'
  ss -ltn 2>/dev/null || warn 'Cannot inspect listeners.'
else warn 'ss is unavailable; inspect the configured listener manually.'; fi

declare -A seen=()
count=0
read_config() {
  local file=$1 canonical key value name executable permissions
  if [[ ! -r "$file" ]]; then fail "Configuration not readable: $file"; return; fi
  canonical=$(readlink -f -- "$file") || { fail "Cannot resolve configuration: $file"; return; }
  if [[ -n "${seen[$canonical]:-}" ]]; then return; fi
  seen[$canonical]=1
  count=$((count + 1))
  if ((count > 256)); then fail 'Configuration include limit exceeded.'; return; fi
  printf 'READ: %s\n' "$file"
  if [[ "$service_user" =~ ^[A-Za-z_][A-Za-z0-9_-]*$ && $EUID -eq 0 ]] && command -v runuser >/dev/null 2>&1; then
    runuser -u "$service_user" -- test -r "$file" || fail "Service account cannot read configuration: $file"
  fi
  while IFS=$'\t' read -r key value; do
    case "$key" in
      include) read_config "$value" ;;
      include_dir)
        if [[ ! -d "$value" || ! -r "$value" || ! -x "$value" ]]; then
          fail "Include directory not accessible: $value"
        else
          for permissions in "$value"/*.cfg; do
            [[ -e "$permissions" ]] || continue
            read_config "$permissions"
          done
        fi ;;
      command\[*\])
        name=${key#command[}; name=${name%]}
        # Only inspect simple absolute executable paths. Never eval a command.
        executable=${value%%[[:space:]]*}
        if [[ ! "$executable" =~ ^/[A-Za-z0-9_./+-]+$ ]]; then
          warn "Command $name: complex/quoted executable; inspect manually (not executed)."
        elif [[ ! -f "$executable" || ! -x "$executable" ]]; then
          fail "Command $name: executable missing or not executable: $executable"
        elif [[ "$service_user" =~ ^[A-Za-z_][A-Za-z0-9_-]*$ && $EUID -eq 0 ]] && command -v runuser >/dev/null 2>&1; then
          if runuser -u "$service_user" -- test -x "$executable"; then report PASS "Command $name: executable accessible to service account."
          else fail "Command $name: service account cannot execute $executable"; fi
        else
          report INFO "Command $name: executable exists; service-account access not verified."
        fi ;;
      allowed_hosts)
        if [[ -n "$monitor_ip" ]]; then
          if [[ ",${value//[[:space:]]/}," == *",$monitor_ip,"* ]]; then report PASS 'Monitoring address is explicitly listed in allowed_hosts.'
          else warn 'Monitoring address is not an exact allowed_hosts entry; review hostnames/CIDR and actual source address.'; fi
        fi ;;
      server_port|server_address|dont_blame_nrpe|allow_bash_command_substitution|ssl_version|ssl_use_adh|ssl_client_certs)
        printf 'SETTING: %s=%s\n' "$key" "$value" ;;
      ssl_cacert_file|ssl_cert_file|ssl_privatekey_file)
        if [[ -f "$value" && -r "$value" ]]; then report INFO "$key: file exists; trust, dates and service-account access not verified."
        else fail "$key: file missing or not readable by this diagnostic user."; fi ;;
    esac
  done < <(awk '
    /^[[:space:]]*($|#)/ {next}
    {i=index($0,"="); if (!i) next; k=substr($0,1,i-1); v=substr($0,i+1);
     gsub(/^[[:space:]]+|[[:space:]\r]+$/,"",k); gsub(/^[[:space:]]+|[[:space:]\r]+$/,"",v);
     if (k ~ /^command\[/ || k ~ /^(include|include_dir|allowed_hosts|server_port|server_address|dont_blame_nrpe|allow_bash_command_substitution|ssl_version|ssl_use_adh|ssl_client_certs|ssl_cacert_file|ssl_cert_file|ssl_privatekey_file)$/) print k "\t" v}
  ' "$file")
}
read_config "$config"
report INFO 'Commented TLS directives use daemon defaults; they do not disable TLS.'
report INFO 'No plugins, remote checks, firewall inspection or TLS handshakes were executed.'
printf 'RESULT: %s failed checks; %s warnings. Review configuration includes and remote reachability separately.\n' "$failures" "$warnings"
((failures == 0))

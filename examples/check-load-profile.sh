#!/bin/sh
# The plugin path is a trusted, fixed argument in the server's NRPE definition.
set -eu

if [ "$#" -ne 2 ]; then
    echo 'UNKNOWN: expected a fixed plugin path and one load profile'
    exit 3
fi
plugin=$1
case "$2" in
    standard) warning=5,4,3; critical=10,8,6 ;;
    busy) warning=10,8,6; critical=20,16,12 ;;
    *) echo 'UNKNOWN: allowed profiles are standard or busy'; exit 3 ;;
esac
case "$plugin" in
    /*) ;;
    *) echo 'UNKNOWN: the configured plugin path must be absolute'; exit 3 ;;
esac
if [ ! -f "$plugin" ] || [ ! -x "$plugin" ]; then
    echo 'UNKNOWN: configured check_load plugin is unavailable'
    exit 3
fi
exec "$plugin" -w "$warning" -c "$critical"

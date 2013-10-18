#!/bin/bash
# expects as $1 the dnsinput file

[[ -n "$1" ]] || exit 1

parentdir=$(dirname $(readlink -f $0))
source "$parentdir/hookconfig"

# copy static/manual configuration to output, so we can append to it
if [[ -d "$staticdir" ]] ; then
   echo "Incorporating static/manual configuration ..."
   #TODO: check if those exist
   cp "$staticdir/${dnsoutput}_address" "$confdir"
   cp "$staticdir/${dnsoutput}_ip4ptr" "$confdir"
   cp "$staticdir/${dnsoutput}_ip6ptr" "$confdir"
fi

echo "Converting $1 ..."
$dnsconvert_bin --override-output "$1" "$confdir/$dnsoutput"

echo "Restarting MaraDNS to load new zonefiles ..."
$restart_maradns

# vim:set ts=4 sw=4 sts=4 et


#!/bin/bash
# expects as $1 the dnsinput file

parentdir=$(dirname $(readlink -f $0))
source "$parentdir/hookconfig"

if [[ -z "$1" ]] ; then
    $logcommand "converter.sh called with no arguments, exiting"
    exit 1
fi

# $1 should actually match $dnsinput - check needed for incron setup which watches whole $confdir
test "$1" = "$dnsinput" || exit 1

# copy static/manual configuration to output, so we can append to it
if [[ -d "$staticdir" ]] ; then
#   $logcommand "Incorporating static/manual configuration ..."
   cp "$staticdir/${dnsoutput}_address" "$confdir" 2> /dev/null
   cp "$staticdir/${dnsoutput}_ip4ptr" "$confdir" 2> /dev/null
   cp "$staticdir/${dnsoutput}_ip6ptr" "$confdir" 2> /dev/null
fi

$logcommand "Converting $1 ..."
$dnsconvert_bin --override-output "$1" "$confdir/$dnsoutput"

$logcommand "Restarting MaraDNS to load new zonefiles ..."
$restart_maradns

# vim:set ts=4 sw=4 sts=4 et :


#!/usr/bin/env python3
import sys
import argparse
import ipaddress
import re

# network specific configuration

domain = "example.net."
ip4_range = ipaddress.IPv4Network('192.168.0.0/16')
ip6_range = ipaddress.IPv6Network('fd00:f00::/64')

# script configuration

#TODO: enumerate keys, they are used in outConfig later, too
outPathSuffix = { 'arecords': '_address', 'aptrs': '_ip4ptr', 'aaaaptrs': '_ip6ptr' }

debugOut = sys.stderr
nameRegex = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")

# argument handling

argParser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
    description="""Convert DNS configuration.\n
Takes a csv file specifiying name-IP mappings, and outputs MaraDNS zone files.
The csv file uses any whitespace as delimiters, and no quote handling is
enabled. Lines starting with # or containing only whitespace are ignored. Every
other line needs 3 columns:
 - An IPv4 address
 - An IPv6 address
 - A list of hostnames, separated by ','
One of the addresses may be replaced by 'none'.

The output configuration files contain record types A, AAAA and PTR. For PTR
records, the first hostname in the list for the respective address is used.

The input file is only accepted if it is valid and addresses belong into the 
networks, else if the input gets rejected, no output file is touched: 
  {ip4_range} or
  {ip6_range}""".format(ip4_range=ip4_range, ip6_range=ip6_range))

argParser.add_argument('inputfile', help="CSV file specifying host names and addresses")
#TODO: make output default to stdout?
argParser.add_argument('outputprefix',
    help="[Path and] filename prefix to write config to. For address, IPv4 PTR " +
         "and IPv6 PTR record files '{}' '{}' and '{}' are appended, respectively.".format(
         outPathSuffix['arecords'], outPathSuffix['aptrs'], outPathSuffix['aaaaptrs']))

argParser.add_argument('--check-only', '-c', action='store_true', default=False,
    help='Do not output a DNS server config, just check the input')
argParser.add_argument('--override-output', '-O', action='store_true', default=False,
    help="Flush the output files before writing to them")

args = argParser.parse_args()



def handleLine(ip4, ip6, names, outp, generate):
    """
    outConfig - dictionary with output file contents
    generate - if True generate config, if False only check validity
    """

    #print("_{}_\t_{}_\t_{}_".format(ip4, ip6, ' '.join(names)), file=debugOut)

    # at least one address has to be supplied
    if ip4 is None and ip6 is None:
        print("Neither IPv4 nor IPv6 address were specified.", file=debugOut)
        return False

    # there must be at least one name
    if len(names) <= 0:
        print("No names were specified.", file=debugOut)
        return False

    try:
        if ip4 is None:
            ip4addr = None
        else:
            ip4addr = ipaddress.IPv4Address(ip4)
            if not ip4addr in ip4_range:
                print("IPv4 address not in permitted range", file=debugOut)
                return False

        if ip6 is None:
            ip6addr = None
        else:
            ip6addr = ipaddress.IPv6Address(ip6)
            if not ip6addr in ip6_range:
                print("IPv6 address not in permitted range", file=debugOut)
                return False

    except:
        print("Invalid IP address", file=debugOut)
        return False

    for name in names:
        if nameRegex.match(name) is None:
            print("Name '{}' invalid".format(name), file=debugOut)
            return False

    #TODO: check for double addresses
    #TODO: check for double DNS names

    if generate:
        primaryName = names[0]

        if not ip4addr is None:
            for name in names:
                outp['arecords'] += "{name}.{domain}\tA\t{ip} ~\n".format(name=name, ip=ip4, domain=domain)
            ip4_r = ipaddress.IPv4Address(ip4addr.packed[::-1])
            outp['aptrs'] += "{rip}.in-addr.arpa.\tPTR\t{name}.{domain} ~\n".format(rip=ip4_r, domain=domain, name=primaryName)

        if not ip6addr is None:
            for name in names:
                outp['arecords'] += "{name}.{domain}\tAAAA\t{ip} ~\n".format(name=name, ip=ip6, domain=domain)
            ip6_r = '.'.join(ip6addr.exploded.translate({ord(":"): None})[::-1])
            outp['aaaaptrs'] += "{rip}.ip6.arpa.\tPTR\t{name}.{domain} ~\n".format(rip=ip6_r, domain=domain, name=primaryName)

    return True


inputfile = open(args.inputfile, 'r')

outConfig = { 'arecords': str(), 'aptrs': str(), 'aaaaptrs': str() }

generate = not args.check_only

for rawRow in inputfile:
    # comment
    if rawRow.startswith('#'):
        continue

    row = rawRow.split(maxsplit=3)

    # empty line
    if len(row) <= 0:
        continue

    # missing column(s)
    if len(row) < 3:
        sys.exit(1)

    ip4 = row[0]
    ip6 = row[1]
    names = row[2].split(',')

    if 'none' in ip4:
        ip4 = None
    if 'none' in ip6:
        ip6 = None

    if not handleLine(ip4, ip6, names, outp=outConfig, generate=generate):
        sys.exit(1)

if generate:
    print("## A and AAAA config\n{}\n## IPv4 PTRs\n{}\n## IPv6 PTRs\n{}\n".format(outConfig['arecords'], outConfig['aptrs'], outConfig['aaaaptrs']), file=debugOut)

    for conf in outConfig:
        outFile = open(args.outputprefix + outPathSuffix[conf], 'w' if args.override_output else 'a')
        outFile.write(outConfig[conf])
        outFile.write('\n')
        outFile.close()


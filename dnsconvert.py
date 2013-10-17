#!/usr/bin/env python3
import sys
import argparse
import re
import configparser
try:
    import ipaddress
except:
    # for python < 3.3, install ipaddr from your distro or http://code.google.com/p/ipaddr-py/
    import ipaddr as ipaddress


# network specific configuration

configParser = configparser.ConfigParser()
configParser.read('dnsconvert.ini')

#TODO: file existance checking, key existance/validity
domain = configParser['DEFAULT']['domain']
ip4_range = ipaddress.IPv4Network(configParser['DEFAULT']['ip4_range'])
ip6_range = ipaddress.IPv6Network(configParser['DEFAULT']['ip6_range'])

# script configuration

#TODO: enumerate keys, they are used in outConfig later, too
outPathSuffix = { 'arecords': '_address', 'aptrs': '_ip4ptr', 'aaaaptrs': '_ip6ptr' }

debugOut = sys.stderr
nameRegex = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")

# argument handling

argParser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
    description="""Convert DNS configuration.

Takes a csv file specifiying name-IP mappings, and outputs MaraDNS zone files.
The csv file uses any whitespace as delimiters, and no quote handling is
enabled. Lines starting with # or containing only whitespace are ignored. Every
other line needs 3 columns:
 - An IPv4 address
 - An IPv6 address
 - A list of lower-case hostnames, separated by ','
One of the addresses may be replaced by 'none'.

The output configuration files contain record types A, AAAA and PTR. For PTR
records, the first hostname in the list for the respective address is used.

The input file is only accepted if it is valid syntax and addresses belong into the
following networks, else if the input gets rejected, no output file is touched:
  {ip4_range} or
  {ip6_range}""".format(ip4_range=ip4_range, ip6_range=ip6_range))

argParser.add_argument('inputfile', help="CSV file specifying host names and addresses")
#TODO: make outputprefix optional if check-only supplied
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
        print("Neither IPv4 nor IPv6 address were specified for name(s) " + ','.join(names), file=debugOut)
        return False

    # there must be at least one name (currently this is handled by the line-parser, so this should never happen)
    if len(names) <= 0:
        print("No names were specified for {}, {}".format(ip4, ip6), file=debugOut)
        return False

    try:
        if ip4 is None:
            ip4addr = None
        else:
            ip4addr = ipaddress.IPv4Address(ip4)
            if not ip4addr in ip4_range:
                print("IPv4 address not in permitted range " + str(ip4_range), file=debugOut)
                return False

        if ip6 is None:
            ip6addr = None
        else:
            ip6addr = ipaddress.IPv6Address(ip6)
            if not ip6addr in ip6_range:
                print("IPv6 address not in permitted range " + str(ip6_range), file=debugOut)
                return False

    except Exception as e:
        print("Invalid IP address: " + repr(e), file=debugOut)
        return False

    for name in names:
        if nameRegex.match(name) is None:
            print("Invalid name \"{}\", does not match {}".format(name, nameRegex.pattern), file=debugOut)
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

class Counter:
    """holds counts of generated records for statistical purposes"""
    def __init__(self):
        self.A = 0
        self.AAAA = 0
        self.PTR = 0
    def add(self, ip4, ip6, nameCount):
        if not ip4 is None:
            self.A += nameCount
            self.PTR += 1
        if not ip6 is None:
            self.AAAA += nameCount
            self.PTR += 1
counter = Counter()

generate = not args.check_only

for rawLineNo, rawRow in enumerate(inputfile, 1):
    # comment
    if rawRow.startswith('#'):
        continue

    row = rawRow.split()

    # empty line
    if len(row) <= 0:
        continue

    # missing column(s)
    if len(row) != 3:
        print("Ill-formed line {}: {} colums, expected 3".format(rawLineNo, len(row)), file=debugOut)
        sys.exit(1)

    ip4 = row[0]
    ip6 = row[1]
    names = row[2].split(',')

    if 'none' in ip4:
        ip4 = None
    if 'none' in ip6:
        ip6 = None

    if not handleLine(ip4, ip6, names, outp=outConfig, generate=generate):
        print("Error occured on line {}, aborting.".format(rawLineNo), file=debugOut)
        sys.exit(1)

    counter.add(ip4, ip6, len(names))

inputfile.close()

if generate:
    #print("## A and AAAA config\n{}\n## IPv4 PTRs\n{}\n## IPv6 PTRs\n{}\n".format(outConfig['arecords'], outConfig['aptrs'], outConfig['aaaaptrs']), file=debugOut)
    print("""Generation successful.
   A records: {noA}
AAAA records: {noAAAA}
 PTR records: {noPTR}\n""".format(noA=counter.A, noAAAA=counter.AAAA, noPTR=counter.PTR))

    for conf in outConfig:
        outFile = open(args.outputprefix + outPathSuffix[conf], 'w' if args.override_output else 'a')
        outFile.write(outConfig[conf])
        outFile.write('\n')
        outFile.close()

# vim:set ts=4 et sw=4 sts=4


# MaraDNS config writer

Given a server running [MaraDNS](http://maradns.samiam.org/) and a set of people who should be able to alter the configuration of one zone for it. You could give them access to the server, or only the config file, or you use this script:
- copy/clone the files from here to your server
- create a bare git repo on the server, and give push rights to above people
- add hookconfig, pre-receive, and post-receive to the hooks/ directory of the repo, take care that they are executable
- adjust the paths and filenames in hookconfig. The default path for dnsconvert.py points to the directory where the hooks reside
- configure the IP address ranges and domain name in dnsconvert.ini

Any user willing to change the zone configuration then checks out that repo, which should contain mainly one file, $dnsinput. He alters that file, commits, and pushes to the repo. If he did any mistake, the push gets rejected via the pre-receive hook. If a push succeeded, the post-receive hook writes a copy of the $dnsinput file to $confdir.

## trigger maradns to reload config
Upon changing of $confdir/$dnsinput, the converter.sh script calls dnsconvert.py to generate the actual zonefiles for maradns, and restarts the server to load that new configuration.
Running converter.sh can be done in multiple ways:

### Periodically via cron

### Upon change via incron
incron uses inotify to get an event everytime a file changes. So by writing into incrontab

    $confdir/$dnsinput  IN_CLOSE_WRITE  /path/to/converter.sh

you only have to start incrond and everything should work


# MaraDNS config writer

Given a server running [MaraDNS](http://maradns.samiam.org/) and a set of people who should be able to alter the configuration of one zone for it. You could give them access to the server, or only the config file, or you use this script:
- copy/clone the files from here to your server
- create a bare git repo on the server, and give push rights to above people
- add pre-receive and post-receive to the hooks/ directory of the repo
- put hookconfig somewhere where both can access it & add its path to them
- adjust the paths and filenames in hookconfig

Any user willing to change the zone configuration then checks out that repo, which should contain mainly one file, $dnsinput. He alters that file, commits, and pushes to the repo. If he did any mistake, the push gets rejected (via the pre-receive hook). If a push succeeded, the post-receive hook generates the maradns zonefiles in $confdir.
TODO: trigger maradns to reload config


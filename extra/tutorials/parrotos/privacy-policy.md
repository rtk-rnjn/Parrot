
# Privacy Policy #

NOTE: This policy is incomplete (it does not yet cover all the infrastructure of the Parrot Project), we hope to finish it shortly.

### Parrot OS
The Parrot operating system does not include trackers or telemetry from the Parrot team or its partners, and we do not track our users on the system.

Parrot OS is a bundle of many complex programs and subsystems, and each of the programs installed on the system may implement it's own telemetry "features".

The Parrot Security Team does its best to provide a system completely clean from trackers, and no data is collected from our users, but additional programs installed on the system by the end user may change this statement. It is up to the end user to make sure that newly installed programs don't ship their own telemetry if privacy is required.

### Parrot's Content Delivery Network

What do these servers actually do? What kind of private information is stored? How is it stored? And what happens if an edge node is cloned and analyzed?

The edge nodes do not host private information of the users, only our master servers host user information.

The edge servers are owned by us, we can delete servers, migrate them, deploy new ones, change providers etc. We can force users in a country to stay away from a particular node and transit the parrot network from a node in another country if we beieve that such countries or providers may inspect user traffic.

We log user activities from the web server logs and use log analyzers to investigate uncommon (malicious) activities and spot possible intrusions or cyber attacks.

Sometimes we collect statistical usage data on our infrastructure usage (downloads, website hits, unique visitors, geographical distribution etc). Such data is aggregate and does not contain personal user information, and ip addresses and other components useful to identify specific users are stripped out before the data aggregation, or sometimes they are not collected at all.

We do NOT log user activities on some services, like the DNS resolvers, to respect user privacy, and we do not collect user information if we don't have a technical reason to log it.

Our sysadmin is the only person authorized to access the servers and handle the logs, and no third parties have access to such data.

The only private information directly visible from goaccess is the ip address of the users, but the servers already have automatic protections to ban misbehaving ip addresses, We store ip addresses temporarily in case of cyberattacks against our web infrastructure.

Personal user data is not stored on our CDN edge nodes, so we can keep user data as safe as possible on the central infrastructure where authorities or third parties can’t take them without our approval.

We periodically delete logs from servers when we are sure that no attacks were received in that period of time, and we shred them for security before restarting the service.

When we dismiss a dedicated server or a VPS, we manually shred the hard disk with random data from a recovery unit to make data unrecoverable before the service deletion.

We have never received a warrant since we began this project. Please note our [warrant canary](<./warrant-canary.md>).


### The Parrot Project's OpenNIC DNS Servers


We provide free DNS resolvers for the OpenNIC network. These servers have logs disabled by default.

There is a tiny log buffer that hosts the latest service hits for technical purposes, allowing the system to identify and automatically ban ip addresses abusing the service.
The temporary log is just a buffer that keeps a bunch of recent elements, and old entries disappear
automatically as new requests come in. It is the standard behavior of the DNS resolver we use (PowerDNS).

Since DNS logs are disabled, and the abuse prevention system is completely automatic, we don't have systems to manually analyze such logs, and we don't perform direct or indirect analysis of DNS services usage.

        
Last updated 25 Apr 2019

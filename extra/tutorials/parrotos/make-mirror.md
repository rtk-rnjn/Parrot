# Make your own mirror #

You can set up a Parrot archive mirror on your server for personal or public usage by following the steps below.


### Make sure to have enough free space ###

You can sync the entire repository or pick just the ISO images.

Make sure to have enough free space to host a mirror, and be ready for future upgrades as the archive size fluctuates.

The current archive size is available here [archive.parrotsec.org/parrot/misc/archive-size.txt](https://deb.parrotsec.org/parrot/misc/archive-size.txt)


### Choose the upstream server ###

We handle several domains for repository syncing services, we suggest you use `rsync.parrot.sh` for automatic and failproof setups, but upstream settings can be adjusted in case of specific needs.

Feel free to contact the Parrot team if you have specific mirroring needs or bandwidth limitations. We can provide you dedicated upstream sources or professional support for your mirror.

<pre>
Main Mirror Director:
    rsync.parrot.sh

Global Zones (read the notes):
    EMEA:
        emea.rsync.parrot.sh
    NCSA:
        ncsa.rsync.parrot.sh
    APAC:
        apac.rsync.parrot.sh
</pre>

Single archives may be unavailable or replaced from time to time.

`rsync.parrot.sh` is automatically balanced between all the available mirrors and will give you zero downtimes.


### Download the archive ###

If you sync the entire archive with the below instructions, you do NOT need to synchronize the ISO archive. ISO files are included by default!

#### Sync the repository ####

    rsync -Pahv --delete-after rsync://rsync.parrot.sh:/parrot /var/www/html/parrot

#### Configure a cronjob ####

launch the following command:

    crontab -e

and add the following content to the crontab file:

    */10 * * * * flock -xn /tmp/parrot-rsync.lock -c 'rsync -aq --delete-after rsync://rsync.parrot.sh:/parrot /var/www/html/parrot'



### Download the ISO archive only ###

Do not sync the ISO archive if you are already synchronizing the full archive with the above instructions. ISO files are already provided with the instructions in the precedent paragraph.

use the following instructions if you want to sync only the ISO files.

#### Sync the repository ####

    rsync -Pahv --delete-after rsync://rsync.parrot.sh:/parrot-iso /var/www/html/parrot

#### Configure a cronjob ####

launch the following command:

    crontab -e

and add the following content to the crontab file:

    30 2 * * * flock -xn /tmp/parrot-rsync.lock -c 'rsync -aq --delete-after rsync://rsync.parrot.sh:/parrot-iso /var/www/html/parrot


### Expose your mirror via rsync ###

Your mirror can be exposed via rsync to allow other people to sync from you and to allow our mirror director to periodically scan your mirror and perform indexing and health checks.

Rsync exposure is mandatory to add your mirror to our official list.

The following instructions will set up rsync and expose the parrot archive in compliance with our standards on a debian/ubuntu server. Minor adjustments are required for other non-apt systems.

install rsync with:

    sudo apt install rsync

edit /etc/rsyncd.conf with nano:

    sudo nano /etc/rsyncd.conf

paste the following settings in the config file and save it:

    [parrot]
            comment = Parrot OS - full archive [rsync.parrot.sh/parrot]
            path = /var/www/html/parrot/
            hosts allow = *
            #hosts deny = *
            list=true
            uid=www-data
            gid=www-data
            read only = yes
            use chroot=yes
            dont compress # for better performance
    
    [parrot-iso]
            comment = Parrot OS - ISO files only [rsync.parrot.sh/parrot-iso]
            path = /var/www/html/parrot/
            exclude = pool dists
            hosts allow = *
            list=true
            uid=www-data
            gid=www-data
            read only = yes
            use chroot=yes
            dont compress


Enable the rsync service:

    sudo systemctl enable rsync    

Start the rsync service:

    sudo service rsync start


### Make your mirror official ###

If you want your mirror to be added to our official mirrors list and to our mirror directors, email us at `team AT parrotsec DOT org`

have fun :)
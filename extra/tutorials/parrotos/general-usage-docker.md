# General Usage Instructions and Examples #

#### Launch a container ####

    docker run --name pcore-1 -ti parrotsec/core

<div class="panel panel-info">
  <div class="panel-heading">
    <i class="fa fa-info-circle badge" aria-hidden="true"></i>

**Note**

  </div>
  <div class="panel-body">
  the pcore-1 name is arbitrary and can be customized
  </div>
</div>

#### Stop the container ####

    docker stop pcore-1

#### Resume a previously-stopped container ####

    docker start pcore-1

#### Remove a container after use ####

    docker rm pcore-1

#### List all the instantiated containers ####

    docker ps -a

#### Start multiple containers ####

on terminal 1 -> `docker run --name pentest1 -ti parrotsec/security` \
on terminal 2 -> `docker run --name pentest2 -ti parrotsec/security` \
on terminal 3 -> `docker run --name msf-listener -ti parrotsec/tools-metasploit` \

#### Remove all the containers ####

    docker rm $(docker ps -qa)

#### Start a container and automatically remove it on exit ####

    docker run --rm -ti parrotsec/core

## Use Volumes to share files with the host:
It is a good practice to not keep persistent docker containers, but to remove them on every use and make sure to save important files on a docker volume.

The following command creates a **work** folder inside the current directory and mounts it in /work inside the container.

    docker run --rm -ti -v $PWD/work:/work parrotsec/core

#### Use Volumes to share files across multiple containers ####

on terminal 1 -> `docker run --name pentest -ti -v $PWD/work:/work parrotsec/security` \
on terminal 2 -> `docker run --rm --network host -v $PWD/work:/work -ti parrotsec/security` \
on terminal 3 -> `docker run --rm -v $PWD/work:/work -ti parrotsec/tools-metasploit` \

#### Open a port from the container to the host ####

Every docker container has its own network space connected to a virtual LAN.

All the traffic from within the docker container will be NATted by the host computer.

If you need to expose a port to other machines outside your local computer, use the following example:

    docker run --rm -p 8080:80 -ti parrotsec/core

Note that the first port is the port that will be opened on your host, and the second one is the container port to bind to.

Here is a reference usage of the **-p** flag:

`-p <host port>:<container port>` (e.g. `-p 8080:80`) \
`-p <host port>:<container port>/<protocol>` (e.g. `-p 8080:80/tcp`) \
\
`-p <address>:<host port>:<container port>` (e.g. `-p 192.168.1.30:8080:80`) \
in case of multiple addresses on host network.

#### Use network host instead of docker NAT ####

Every docker container has its own network space connected to a virtual LAN.

All the traffic from within the docker container will be NATted by the host computer.

If you need to make the docker container share the same networking space of the host machine, then use the **--network host** flag as shown below

    docker run --rm --network host -ti parrotsec/core

<div class="panel panel-info">
  <div class="panel-heading">
    <i class="fa fa-info-circle badge" aria-hidden="true"></i>

**Note 1**

  </div>
  <div class="panel-body">
  every port opened in the container will be opened on the host as well.
  </div>
</div>


<div class="panel panel-info">
  <div class="panel-heading">
    <i class="fa fa-info-circle badge" aria-hidden="true"></i>

**Note 2**

  </div>
  <div class="panel-body">
  you can perform packet sniffing on the host network.
  </div>
</div>


<div class="panel panel-info">
  <div class="panel-heading">
    <i class="fa fa-info-circle badge" aria-hidden="true"></i>

**Note 3**

  </div>
  <div class="panel-body">
  iptables rules applied inside the container will take effect on the host as well.
  </div>
</div>

## File and Directory Permissions ##

With GNU/Linux, all the files of the system belong to a user and a group. The owner of a file is the user who created it and the main group of this file is that of the user who created it. For example, in the other chapters, we worked with a user account simply called **user**. If this user creates a file, it belongs to the parrot user and the default group of the parrot user. For this reason, we often use the `sudo` command to be able to read, modify or execute files and programs of the system or make changes in the permissions of the files in question.

Let's analyze the output of the command `ls -l`

	┌─[root@parrot]─[/home/parrot]
	└──╼ # ls -l archive.txt 
	-rw-rw-r-- 1 parrot hackers    0    oct 16 12:32 archive.txt
	drwxr-xr-x 3 parrot hackers  4096   oct 15 16:25 scripts

The output of the command `ls -l` indicates whether it is a file (-) or directory (d), the permissions of the file/directory (rw-rw-r--), the following field (indicates the number of files/directories) user and group to which it belongs (parrot hackers), size (0), last modification date (Oct 16 12:32) and name (file.txt and scripts). Let's start with the fields permission, user, and group. We will focus on the first field (file permissions). In Linux, the permission management that the users and the groups of users have on the files and folders is carried out using a simple scheme of three types of permission:

**Read** permission, represented by the "**r**" letter.

**Write** permission, represented by the "**w**" letter.

**Execution** permission, repersented by the "**x**" letter.

The meaning of the permissions is different for files and folders. We will explain each of these.

In the case of a *.txt* file, it has the following permissions:

	Owner	Group	Other Users
	r  w  -	r  w  -	r  -  -
This means that all the system users have permission to read this file, but only the owner and the members of the owner group can make modifications to this file.

To calculate the value, we will base the sum of its decimal values according to the following correspondence:

|Permission	|r |w| x |
|-----------------------------------|--|---|----|
|Decimal Value	|4| 2 | 1 |

That is, the decimal value for the read permission is 4, the value for write permission is 2 and the value for execute permission is 1. The possible values are as follows:




| Permission | Value |
|------------|--------|
|    rwx     |   7   |
|  rw-  |   6   |
|  r-x    |   5   |
|  r--     |   4   |
|  -wx  |   3   |
|  -w-   |   2   |
|  --r     |   1 |
|   ---   |  0   |




Therefore, we come to the following conclusion: 

| Permission     |   Value  |
|-----------------------|-------------|
| rwx rwx rwx  |   777      |
| rwx r-x r--        |   754      |
| r-x r- - ----------- |   540      |

Having this clear, we can use "chmod", which helps us manage the files and folders' permissions.

#### chmod ####

Basic syntax of chmod:

	$ chmod [mode] [permissions] [file or directory]

In the example below, we have a script folder in which not all scripts have the execute permission.

	┌─[root@parrot]─[/home/parrot]
	└──╼ #ls -l scripts/
	total 16
	-rw-r--r-- 1 parrot hackers  932 oct 18 01:06 ddos-detect.py
	-rwxr-xr-x 1 parrot hackers  235 oct 18 01:06 ping.sh
	-rwxr-xr-x 1 parrot hackers  780 oct 18 01:17 wireless-dos-ids.py
	-rw-r--r-- 1 parrot hackers 1587 oct 18 01:05 wireless-dos.py

As you can see in the execution of `ls -l scripts/`, some scripts have execution permissions for all the system users (which is not recommended), while others do not have execution permission even for the owner user. To correct this error we apply the following:

	┌─[root@parrot]─[/home/parrot]
	└──╼ #chmod -R 770 scripts/

	┌─[root@parrot]─[/home/parrot]
	└──╼ #ls -l scripts/
	total 16
	-rwxrwx--- 1 parrot hackers  932 oct 18 01:06 ddos-detect.py
	-rwxrwx--- 1 parrot hackers  235 oct 18 01:06 ping.sh
	-rwxrwx--- 1 parrot hackers  780 oct 18 01:17 wireless-dos-ids.py
	-rwxrwx--- 1 parrot hackers 1587 oct 18 01:05 wireless-dos.py

Now the owner user and the members of the owner group have read, write and execute permissions, while other users of the system do not have access to this file.

Another way to add or remove permissions is using these modes:
\
`a` --> indicates that it will be applied to all
\
`u` --> indicates that it will be applied to the user
\
`g` --> indicates that it will be applied to the group
\
`o` --> indicates that it will apply to others
\
`+` --> indicates that the permission is added
\
`-` --> indicates  that the permission is removed
\
`r` --> indicates  read permission
\
`w` --> indicates write permission
\
`x` --> indicates execution permission
\

The basic syntax for using "chmod" with these modes is as follows:

    chmod [a | u | g | o] [+ | -] [r | w | x]

To who this is applied, add or remove permissions, and the type of permission that is to be add or removed.

Possible combinations:

- `a+r` Read permissions for all
- `+r` As before, if nothing is indicated, 'a' is assumed.
- `og-x` Removes execution permission from all but the user.
- `u+rwx` Gives all the permissions to the user.
- `o-rwx` Remove the permissions from the others.

Example of use:

	┌─[root@parrot]─[/home/parrot]
	└──╼ #chmod -R og-x scripts/

	┌─[root@parrot]─[/home/parrot]
	└──╼ #ls -l scripts/
	total 16
	-rwxrw---- 1 parrot hackers  932 oct 18 01:06 ddos-detect.py
	-rwxrw---- 1 parrot hackers  235 oct 18 01:06 ping.sh
	-rwxrw---- 1 parrot hackers  780 oct 18 01:17 wireless-dos-ids.py
	-rwxrw---- 1 parrot hackers 1587 oct 18 01:05 wireless-dos.py

If we analyze the the previous results, we notice how the execution permissions have been eliminated for all system users, including the members of the owner group, except the owner user, which conserves the read, write and execute permissions.

#### chown ####

chown (Change owner) is another system utility that allows us to make changes to the ownership of the files, it looks like "chmod" but the function it performs is different. As the name implies, it is used to change the owner of a file or folder.

Its basic syntax is as follows:

	$ chown [options] [owner]: [group (optional)] [files or directories]

Chown options:
\
`-R` --> Recursively changes the owner of the directories along with all its contents.
\
`-v or --verbose` --> Used to show a more descriptive output.
\
`--version` --> See the version number of the program.
\
`-dereference` --> Acts on symbolic links instead of on the destination.
\
`-h or --no-deference` --> In the case of symbolic links, change the owner of the destination instead of the link itself.
\
`--reference` --> Changes the owner of a file, taking as reference the owner of the other.
\

Examples of use:

	┌─[root@parrot]─[/home/parrot]
	└──╼ #ls -l scripts/
	total 16
	-rwxrw---- 1 parrot parrot  932 oct 18 01:06 ddos-detect.py
	-rwxrw---- 1 parrot parrot  235 oct 18 01:06 ping.sh
	-rwxrw---- 1 parrot parrot  780 oct 18 01:17 wireless-dos-ids.py
	-rwxrw---- 1 parrot parrot 1587 oct 18 01:05 wireless-dos.py

	┌─[root@parrot]─[/home/parrot]
	└──╼ #chown -R root:root scripts/

	┌─[root@parrot]─[/home/parrot]
	└──╼ #ls -l scripts/
	total 16
	-rwxrw---- 1 root root  932 oct 18 01:06 ddos-detect.py
	-rwxrw---- 1 root root  235 oct 18 01:06 ping.sh
	-rwxrw---- 1 root root  780 oct 18 01:17 wireless-dos-ids.py
	-rwxrw---- 1 root root 1587 oct 18 01:05 wireless-dos.py

In the previous example, we can see how the user and group owner of all the files that are in the scripts directory have changed. Let's see an example where we are only going to change the owner use.
	
	┌─[root@parrot]─[/home/parrot]
	└──╼ #ls -l scripts/
	total 16
	-rwxrw---- 1 root root  932 oct 18 01:06 ddos-detect.py
	-rwxrw---- 1 root root  235 oct 18 01:06 ping.sh
	-rwxrw---- 1 root root  780 oct 18 01:17 wireless-dos-ids.py
	-rwxrw---- 1 root root 1587 oct 18 01:05 wireless-dos.py

	┌─[root@parrot]─[/home/parrot]
	└──╼ #chown -R parrot scripts/

	┌─[root@parrot]─[/home/parrot]
	└──╼ #ls -l scripts/
	total 16
	-rwxrw---- 1 parrot root  932 oct 18 01:06 ddos-detect.py
	-rwxrw---- 1 parrot root  235 oct 18 01:06 ping.sh
	-rwxrw---- 1 parrot root  780 oct 18 01:17 wireless-dos-ids.py
	-rwxrw---- 1 parrot root 1587 oct 18 01:05 wireless-dos.py

You can see how the user who owns all the files within the scripts directory changed to parrot.

#### chgrp ####

The chgrp command is used to change the group to which a file or directory belongs. Its basic syntax is the following:

	$ chgrp [options] [file (s)] or [directory (s)]

Options

`-R` -> Recursively changes the group to which the directories belong together with all their contents.

`-v (or --verbose)` -> Used to show a more descriptive output.

`--version` -> See the version number of the program.

`--dereference` -> Acts on symbolic links instead of on the destination.

`-h (or --no-dereference)` -> In the case of symbolic links, change the destination group instead of the link itself.

`--reference` -> Change the group of a file taking as reference the owner of another.

They are practically the same **"chown"** options, with the difference that **"chgrp"** only changes the group that owns files and / or directories, keeping the user owner.

Example of use of chgrp:

	┌─[root@parrot]─[/home/parrot]
	└──╼ #ls -l scripts/
	total 16
	-rwxrw---- 1 parrot parrot  932 oct 18 01:06 ddos-detect.py
	-rwxrw---- 1 parrot parrot  235 oct 18 01:06 ping.sh
	-rwxrw---- 1 parrot parrot  780 oct 18 01:17 wireless-dos-ids.py
	-rwxrw---- 1 parrot parrot 1587 oct 18 01:05 wireless-dos.py

	┌─[root@parrot]─[/home/parrot]
	└──╼ #chown -R root:root scripts/

	┌─[root@parrot]─[/home/parrot]
	└──╼ #ls -l scripts/
	total 16
	-rwxrw---- 1 root root  932 oct 18 01:06 ddos-detect.py
	-rwxrw---- 1 root root  235 oct 18 01:06 ping.sh
	-rwxrw---- 1 root root  780 oct 18 01:17 wireless-dos-ids.py
	-rwxrw---- 1 root root 1587 oct 18 01:05 wireless-dos.py

In this example, we can see how the user and group owner of all the files that are in the scripts directory have changed. Let's see an example where we are only going to change the owner user.

	┌─[root@parrot]─[/home/parrot]
	└──╼ #ls -l scripts/
	total 16
	-rwxrw---- 1 root root  932 oct 18 01:06 ddos-detect.py
	-rwxrw---- 1 root root  235 oct 18 01:06 ping.sh
	-rwxrw---- 1 root root  780 oct 18 01:17 wireless-dos-ids.py
	-rwxrw---- 1 root root 1587 oct 18 01:05 wireless-dos.py

	┌─[root@parrot]─[/home/parrot]
	└──╼ #chown -R parrot scripts/

	┌─[root@parrot]─[/home/parrot]
	└──╼ #ls -l scripts/
	total 16
	-rwxrw---- 1 parrot root  932 oct 18 01:06 ddos-detect.py
	-rwxrw---- 1 parrot root  235 oct 18 01:06 ping.sh
	-rwxrw---- 1 parrot root  780 oct 18 01:17 wireless-dos-ids.py
	-rwxrw---- 1 parrot root 1587 oct 18 01:05 wireless-dos.py

You can see how the group that owns the files wireless-dos-ids.py and wireless-dos.py changed from root to parrot user.

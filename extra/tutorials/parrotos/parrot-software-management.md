# Parrot Software Management #

In this chapter, we will introduce the APT package manager for Parrot. A program is a series of instructions written in programming languages such as C, Go, Nim or Rust (to name a few). These instructions are stored in text files called sources. To work in our systems, they must be converted to machine language. This step is called compilation. The compilation generates one or several files, understandable by the system, called binaries.

The user doesn't need to compile the sources of each program as the developers are responsible for compiling and generating the respective binaries. A program can carry not only the executable but a series of files. The developers combine such software into a file called a package. Two of the most well-known are RPM packages and DEB packages. RPM was developed by Red Hat and DEB by Debian. Parrot uses the DEB format.

To compile programs, often 3rd party libraries and other programs are necessary. If we tried to compile a program that had dependencies with other libraries and other programs, we would install these "dependencies" before its compilation. Likewise, if we want to install a binary we will need to have installed the necessary dependencies for its correct operation.

To manage these dependencies and the "package" installation, package managers have been created. There are numerous package managers, some graphical and others via the command line. In this chapter, we will see one of the most famous, created by the Debian developers, and the one used by Parrot: **APT**.

The main functions of a package manager must be:

- Software searching
- Software installation
- Software update
- System update
- Dependency management
- Software removal

The package manager must check in a given location (it can be a local directory or a network address) for the availability of such software. The locations are called repositories. The system maintains configuration files to check repository locations.

## List of Repositories ##

Although in Parrot it is not necessary (nor recommended) to add new repositories or modify existing ones, we will see where we can configure them. In the file system, under the path "/etc/apt/sources.list.d", we find the file parrot.list. The content of this file should be:

	## stable repository
	deb http://deb.parrotsec.org/parrot stable main contrib non-free
	#deb-src http://archive.parrotsec.org/parrot stable contrib non-free

With this, we make sure we have the correct repository list. In this location the Parrot developers keep the packages updated.

## Package Manager (APT) ##

The Parrot package manager is apt. Amongst other things,this manager is responsible for installing packages, checking dependencies, and updating the system. Let's see what we can do with it. We will see the most common options below. For more in-depth instructions, view the man pages for each of the following commands: apt, apt-get, apt-cache, dpkg.

Search for a package or text string:

    apt search <text_string>

\
Show package information:

    apt show <package>

\
Show package dependencies:

    apt depends <package>

\
Show the names of all the packages installed in the system:

    apt list --installed
	
\
Install a package:

    apt install <package>

\
Uninstall a package:

    apt remove <package>

\
Delete a package including its configuration files:

    apt purge <package>

\
Delete automatically those packages that are not being used (be careful with this command, due to apt's hell dependency it may delete unwanted packages): 

    apt autoremove

\
Update the repositories information:

    apt update

\
Update a package to the last available version in the repository:

    apt upgrade <package>
	
\
Update the full distribution. It will update our system to the next available version:

    parrot-upgrade

\
Clean caches, downloaded packages, etc:

    apt clean && apt autoclean

\
These are just some examples. If more information is required, you should check the manual page (man 8 apt).

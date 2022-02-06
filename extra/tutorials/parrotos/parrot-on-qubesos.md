# Parrot on QubesOS #

There are two ways to create a ParrotOS VM on QubesOS for now.

### Option 1 - Create an HVM ###

1. Download any ParrotOS x86_64 image you want.

2. [Create](https://www.qubes-os.org/doc/standalones-and-hvms/#command-line) a new HVM ([Hardware-assisted Virtual Machine](https://www.qubes-os.org/doc/glossary/#hvm)).
    

3. Start the HVM with attached CD/DVD.

    
        [user@dom0 ~]$ qvm-start <hvm-name> --cdrom <vm-name>:/home/user/Downloads/<iso-name>.iso



### Option 2 - Build a ParrotOS TemplateVM on top of a Debian TemplateVM ###

**WARNING**: This documentation cannot guarantee that any PGP key you download from the Internet is authentic. Always get a trusted key fingerprint via other channels and always check any key you download against your trusted copy of the fingerprint.

This step is required since by (security) default a TemplateVM does not have direct Internet connectivity. Users understanding the risks of enabling such access can change this configuration in firewall settings for the TemplateVM.

*Note*: The prompt on each line shows where each command should be entered (@dom0, @parrot, @xxxx-dvm, @debian-<X>). 

1. Retrieve the official ParrotOS GPG key using a [DispVM](https://www.qubes-os.org/doc/how-to-use-disposables/).

    
    
        [user@xxxx-dvm ~]$ gpg --keyserver hkp://keys.gnupg.net --recv-key 3B3EAB807D70721BA9C03E55C7B39D0362972489
    \

        [user@xxxx-dvm ~]$ gpg --list-keys --with-fingerprint 3B3EAB807D70721BA9C03E55C7B39D0362972489 
    \

        [user@xxxx-dvm ~]$ gpg --export --armor 3B3EAB807D70721BA9C03E55C7B39D0362972489 > parrot-key.asc
    

2. DO NOT TURN OFF THE DISPVM. The parrot-key.asc file will be copied to the ParrotOS template in a further step.

3. Make sure the key is the authentic ParrotOS key.

### Create a ParrotOS TemplateVM ###

These instructions will show you how to upgrade a Debian TemplateVM to ParrotOS.

1. (Optional) Check for latest Debian stable template and install it (if not already done):

        [user@dom0 ~]$ sudo qubes-dom0-update --action="search all" qubes-template-debian
    
    \

        [user@dom0 ~]$ sudo qubes-dom0-update <latest Debian template>

2. Start,update and close your Debian TemplateVM.

        [user@dom0 ~]$ qvm-start debian-<X>
    \

        [user@dom0 ~]$ qvm-run -a debian-<X> gnome-terminal

    \

        [user@debian-<X> ~]$ sudo apt update

    \

        [user@debian-<X> ~]$ sudo apt upgrade

    \

        [user@dom0 ~]$ qvm-shutdown debian-<X>


3. Clone debian-x TemplateVM

        [user@dom0 ~]$ qvm-clone debian-<X> parrot


4. Check the name of currently used repository in /etc/apt/sources.list and current testing Debian release. Update repository list accordingly

        [user@parrot ~]$ sudo sed -i 's/<current stable>/<current testing>/g' /etc/apt/sources.list

    \

        [user@parrot ~]$ sudo sed -i 's/<current stable>/<current testing>/g' /etc/apt/sources.list.d/qubes-r<X>.list

e.g. in this example we update stretch stable repository to buster testing repository

    [user@parrot ~]$ sudo sed -i 's/stretch/buster/g' /etc/apt/sources.list

  \

    [user@parrot ~]$ sudo sed -i 's/stretch/buster/g' /etc/apt/sources.list.d/qubes-r<X>.list

5. Upgrade parrot template to latest Debian testing release

        [user@parrot ~]$ sudo apt update && sudo apt full-upgrade

    \

        [user@parrot ~]$ sudo apt autoremove

Note: During execution of a full-upgrade command read carefully list of packages to be removed. If it contains qubes-* packages, terminate operation and try to resolve qubes-* packages missing dependencies first.

6. Copy the ParrotOS GPG key from the DispVM to the new template:

        [user@xxxx-dvm ~]$ qvm-copy-to-vm parrot parrot-key.asc

Turn off the DispVM.

7. Add the ParrotOS GPG key to the list of keys trusted to authenticate packages:

        [user@parrot ~]$ cat /home/user/QubesIncoming/dispXXX/parrot-key.asc | sudo apt-key add -

The above command should return OK in a single line.

8. Attempt an update on the new TemplateVM

        [user@parrot ~]$ sudo cat <<EOF > /etc/apt/sources.list.d/parrot.list
        # ParrotOS repository
        deb http://deb.parrotsec.org/parrot stable main contrib non-free
        #deb-src http://deb.parrotsec.org/parrot stable main contrib non-free
        EOF

    \

        [user@parrot ~]$ sudo apt update

    \

        [user@parrot ~]$ sudo apt full-upgrade

    \

        [user@parrot ~]$ sudo apt autoremove

    \

        [user@parrot ~]$ sudo apt install parrot-core parrot-archive-keyring parrot-drivers parrot-skel


9. Shut down and trim the new TemplateVM

        [user@dom0 ~]$ qvm-shutdown parrot

    \
    
        [user@dom0 ~]$ qvm-trim-template parrot


10. Ensure a terminal can be opened in the new TemplateVM

        [user@dom0 ~]$ qvm-run -a parrot gnome-terminal



#### Install the penetration testing tools (optional) ####

At this point you should have a working template and you can install the tools you need.

1. Resize the template disk image if you plan on installing the full ParrotOS distribution. For example, to install parrot-tools-full you must grow the size of the VM system from 10GB to at least 20GB.

2. Install ParrotSec penetration testing tools:

        [user@parrot ~]$ sudo apt install parrot-tools-full


(Optional) Customize the template’s home directory (e.g. install your licensed copy of Burp Suite Professional)

#### Use the TemplateVM ####
The template is ready to be used. You can now spin up AppVMs based on the parrot template.

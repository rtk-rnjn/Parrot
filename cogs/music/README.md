# `Lavalink.jar`

Download the latest release of [lavalink](https://github.com/freyacodes/Lavalink/releases) from there official repository.

---

### Requirements

- Java 11* LTS or newer required.
- OpenJDK or Zulu running on Linux AMD64 is officially supported.

---

## To install `java`

```bash
sudo apt update
```

```bash
$ sudo apt install default-jdk
Setting up default-jdk-headless (2:1.11-72build2) ... 
Setting up openjdk-11-jdk:amd64 (11.0.15+10-0ubuntu0.22.04.1) ... 
using /usr/lib/jvm/java-11-openjdk-amd64/bin/jconsole 
Setting up default-jdk (2:1.11-72build2) ...
```

```bash
$ sudo apt install default-jre
Setting up default-jre (2:1.11-72build2) ...
```

```bash
$ update-alternatives --config java
There is only one alternative in link group java (providing /usr/bin/java): 
/usr/lib/jvm/java-11-openjdk-amd64/bin/java
```

```bash
sudo nano /etc/environment  # Add JAVA_HOME to the environment
```

```bash
JAVA_HOME="JAVA_HOME="/lib/jvm/java-11-openjdk-amd64/bin/java"  # Paste the JAVA_HOME assignment at the bottom of the file
```

```bash
source /etc/environment  # Then force the Ubuntu terminal to reload the environment configuration file
```

```bash
echo $JAVA_HOME # You should then be able to echo the JAVA_HOME environment variable in an Ubuntu terminal window
/lib/jvm/java-11-openjdk-amd64/bin/java
```

![image](https://user-images.githubusercontent.com/37435729/180354944-26ed7e4d-0a69-43ff-a63d-2790db8e446b.png)

---

### You can start the lavalink server with the following command

```bash
pm2 start "java -jar Lavalink.jar" --name lavalink
```

The Parrot Project not only delivers a ready-to-use system in the ISO format, but it also provides a vast amount of additional software that can be installed apart from the official parrot repository.

The Parrot repository is used to provide officially supported software, system updates and security fixes.

# The mirrors network #

The software in the parrot archive is delivered in form of deb packages, and these packages are served through a vast network of mirror servers that provide the same set of packages distributed all around the world for faster software delivery.

The Parrot system is configured to use the central parrot archive directors. The Parrot directors are special servers that collect all the requests of the end users and redirect them to the geographically nearest download server available for the user who made the request.

If you want and can, you can make your own mirror for Parrot following [this procedure](./mirrors-list.html#make-your-own-mirror).

### Security measures ###

The Parrot Mirror Network is secured by centralized digital signatures and the mirrors can't inject fake updates.

If an evil mirror tries to inject a fake package, the Parrot system will automatically refuse to download and install it, and will raise an alert message.

This security measure implemented in APT (the Parrot/Debian package manager) is very efficient and reliable because digital signatures are applied offline by the Parrot archive maintainer, and not by the mirror servers, ensuring direct and secure developer-to-user chain of trust.

## Configuration and custom setup ##

The APT package manager uses `/etc/apt/sources.list` and any *.list* file found in the `/etc/apt/sources.list.d/` directory.


<div class="panel panel-info">
  <div class="panel-heading">
    <i class="fa fa-info-circle badge" aria-hidden="true"></i>

**Note**

  </div>
  <div class="panel-body">
  /etc/apt/sources.list is EMPTY and the default APT configuration is located at /etc/apt/sources.list.d/parrot.list.
  </div>
</div>

### Content of /etc/apt/sources.list.d/parrot.list ###

    deb https://deb.parrot.sh/parrot/ rolling main contrib non-free
    #deb-src https://deb.parrot.sh/parrot/ rolling main contrib non-free
    deb https://deb.parrot.sh/parrot/ rolling-security main contrib non-free
    #deb-src https://deb.parrot.sh/parrot/ rolling-security main contrib non-free
    
## Other mirrors for manual configuration ##

### Worldwide (CDN) ###

| Location<br>Mirror ID<br>bandwidth | Provider Name | URL | APT config string |
|:----------------------------------|:---------------:|:-----|:-------------------|
|Parrot Infrastructure<br>/<br>/|Parrot Infrastructure|[deb.parrot.sh/parrot](https://deb.parrot.sh/parrot)|<sub>deb https://deb.parrot.sh/parrot rolling main contrib non-free</sub>|
|Azure<br>/<br>/|Microsoft Azure|[edge1.parrot.run/parrot](https://edge1.parrot.run/parrot)|<sub>deb https://edge1.parrot.run/parrot rolling main contrib non-free</sub>|
|AWS<br>/<br>/|AWS - Amazon Web Services|[edge2.parrot.run/parrot](https://edge2.parrot.run/parrot)|<sub>deb https://edge2.parrot.run/parrot rolling main contrib non-free</sub>|
|BunnyCDN<br>/<br>/|Bunny.net|[edge3.parrot.run](https://edge3.parrot.run)|<sub>deb https://edge3.parrot.run rolling main contrib non-free</sub>|
|Alibaba<br>/<br>10 Gbps|Alibaba Cloud|[mirrors.aliyun.com/parrot](https://mirrors.aliyun.com/parrot)|<sub>deb https://mirrors.aliyun.com/parrot rolling main contrib non-free</sub>|

### NCSA ###
North Central and South Americas

| Location<br>Mirror ID<br>bandwidth | Provider Name | URL | APT config string |
|:----------------------------------|:---------------:|:-----|:-------------------|
|Massachussetts<br>MIT<br>1 Gbps|SIPB MIT|[mirrors.mit.edu/parrot](http://mirrors.mit.edu/parrot/)|<sub>deb http://mirrors.mit.edu/parrot/ rolling main contrib non-free</sub>|
|New York<br>Clarkson<br>1 Gbps|Clarkson University|[mirror.clarkson.edu/parrot](https://mirror.clarkson.edu/parrot/)|<sub>deb https://mirror.clarkson.edu/parrot/ rolling main contrib non-free</sub>|
|Oregon<br>Osuosl<br>1 Gbps|Oregon State University - Open Source Lab|[ftp.osuosl.org/pub/parrotos](https://ftp.osuosl.org/pub/parrotos)|<sub>deb https://ftp.osuosl.org/pub/parrotos rolling main contrib non-free</sub>|
|California<br>Berkeley<br>1 Gbps|Berkeley Open Computing Facility|[mirrors.ocf.berkeley.edu/parrot](http://mirrors.ocf.berkeley.edu/parrot)|<sub>deb https://mirrors.ocf.berkeley.edu/parrot/ rolling main contrib non-free</sub>|
|Virginia<br>Leaseweb<br>10 Gbps|Leaseweb|[mirror.wdc1.us.leaseweb.net/parrot](https://mirror.wdc1.us.leaseweb.net/parrot)|<sub>deb https://mirror.wdc1.us.leaseweb.net/parrot rolling main contrib non-free</sub>|
|Ecuador<br>CEDIA<br>100 Mbps|RED CEDIA (National research and education center of Ecuador)|[mirror.cedia.org.ec/parrot](http://mirror.cedia.org.ec/parrot)|<sub>deb https://mirror.cedia.org.ec/parrot/ rolling main contrib non-free</sub>|
|Ecuador<br>UTA<br>100 Mbps|UTA (Universidad Técnica de ambato)|[mirror.uta.edu.ec/parrot](http://mirror.uta.edu.ec/parrot)|<sub>deb https://mirror.uta.edu.ec/parrot/rolling main contrib non-free<</sub>|
|Ecuador<br>UEB<br>100 Mbps|UEB (Universidad Estatal de Bolivar)|[mirror.ueb.edu.ec/parrot](http://mirror.ueb.edu.ec/parrot)|<sub>deb https://mirror.ueb.edu.ec/parrot/ rolling main contrib non-free</sub>|
|Brazil<br>USP<br>1 Gbps|University of Sao Paulo|[sft.if.usp.br/parrot](http://sft.if.usp.br/parrot)|<sub>deb http://sft.if.usp.br/parrot/ main contrib non-free</sub>|
|Canada<br>/<br>/|Emma Samms|[https://mirror.0xem.ma/parrot/](https://mirror.0xem.ma/parrot/)|<sub>deb https://mirror.0xem.ma/parrot/ main contrib non-free</sub>|


### EMEA ###
Europe Middle East and Africa

| Location<br>Mirror ID<br>bandwidth | Provider Name | URL | APT config string |
|:----------------------------------|:---------------:|:-----|:-------------------|
|Italy<br>GARR<br>10 Gbps|GARR Consortium (Italian Research & Education Network)|[parrot.mirror.garr.it/mirrors/parrot](http://parrot.mirror.garr.it/mirrors/parrot)|<sub>deb https://parrot.mirror.garr.it/mirrors/parrot/ rolling main contrib non-free</sub>|
|Germany<br>Halifax<br>20 Gbps|RWTH-Aachen (Halifax students group)|[ftp.halifax.rwth-aachen.de/parrotsec](http://ftp.halifax.rwth-aachen.de/parrotsec)|<sub>deb https://ftp.halifax.rwth-aachen.de/parrotsec/ rolling main contrib non-free</sub>|
|Germany<br>Esslingen<br>10 Gbps|Esslingen (University of Applied Sciences)|[ftp-stud.hs-esslingen.de/pub/Mirrors/archive.parrotsec.org](http://ftp-stud.hs-esslingen.de/pub/Mirrors/archive.parrotsec.org)|<sub>deb https://ftp-stud.hs-esslingen.de/pub/Mirrors/archive.parrotsec.org/ rolling main contrib non-free</sub>|
|Germany<br>Leaseweb<br>10 Gbps|Leaseweb|[mirror.fra10.de.leaseweb.net/parrot](https://mirror.fra10.de.leaseweb.net/parrot)|<sub>deb https://mirror.fra10.de.leaseweb.net/parrot rolling main contrib non-free</sub>|
|Germany<br>pyratelan<br>/|pyratelan|[mirror.pyratelan.org/parrot](https://mirror.pyratelan.org/parrot)|<sub>deb https://mirror.pyratelan.org/parrot rolling main contrib non-free</sub>|
|Netherlands<br>NLUUG<br>10 Gbps|Nluug|[ftp.nluug.nl/os/Linux/distr/parrot](http://ftp.nluug.nl/os/Linux/distr/parrot)|<sub>deb https://ftp.nluug.nl/os/Linux/distr/parrot/ rolling main contrib non-free</sub>|
|Netherlands<br>lyrahosting<br>/|lyrahosting|[mirror.lyrahosting.com/parrot](https://mirror.lyrahosting.com/parrot)|<sub>deb  https://mirror.lyrahosting.com/parrot rolling main contrib non-free</sub>|
|Sweden<br>UMU<br>20 Gbps|ACC UMU (Academic Computer Club, Umea University)|[ftp.acc.umu.se/mirror/parrotsec.org/parrot](http://ftp.acc.umu.se/mirror/parrotsec.org/parrot)|<sub>deb https://ftp.acc.umu.se/mirror/parrotsec.org/parrot/ rolling main contrib non-free</sub>|
|Greece<br>UOC<br>1 Gbps|UoC (University of Crete - Computer Center)|[ftp.cc.uoc.gr/mirrors/linux/parrot](http://ftp.cc.uoc.gr/mirrors/linux/parrot)|<sub>deb https://ftp.cc.uoc.gr/mirrors/linux/parrot/ rolling main contrib non-free</sub>|
|Belgium<br>Belnet<br>10 Gbps|Belnet (The Belgian National Research)|[ftp.belnet.be/archive.parrotsec.org](http://ftp.belnet.be/mirror/archive.parrotsec.org)|<sub>deb http://ftp.belnet.be/mirror/archive.parrotsec.org/ rolling main contrib non-free</sub>|
|Spain<br>Osluz<br>1 Gbps|Osluz (Oficina de software libre de la Universidad de Zaragoza)|[matojo.unizar.es/parrot](http://matojo.unizar.es/parrot)|<sub>deb http://matojo.unizar.es/parrot/ rolling main contrib non-free</sub>|
|Portugal<br>UP<br>1 Gbps|U.Porto (University of Porto)|[mirrors.up.pt/parrot](http://mirrors.up.pt/parrot)|<sub>deb https://mirrors.up.pt/parrot/ rolling main contrib non-free</sub>|
|Denmark<br>Dotsrc<br>10 Gbps|Dotsrc (Aalborg university)|[mirrors.dotsrc.org/parrot](http://mirrors.dotsrc.org/parrot)|<sub>deb https://mirrors.dotsrc.org/parrot/ rolling main contrib non-free</sub>|
|France<br>Cythin<br>100 Mbps|Cythin.com|[parrot.mirror.cythin.com/parrot](https://parrot.mirror.cythin.com/parrot)|<sub>deb https://parrot.mirror.cythin.com/parrot rolling main contrib non-free</sub>|
|France<br>iriseden<br>/|iriseden|[parrot-mirror.iriseden.eu/parrot](https://parrot-mirror.iriseden.eu/parrot)|<sub>deb https://parrot-mirror.iriseden.eu/parrot rolling main contrib non-free</sub>|
|Hungary<br>quantum-mirror<br>700 Mbps|quantum-mirror.hu|[quantum-mirror.hu/mirrors/pub/parrot](https://quantum-mirror.hu/mirrors/pub/parrot)|<sub>deb https://quantum-mirror.hu/mirrors/pub/parrot rolling main contrib non-free</sub>|
|Turkey<br>EB<br>100 Mbps|EB|[turkey.archive.parrotsec.org/parrot](http://turkey.archive.parrotsec.org/parrot)|<sub>deb http://turkey.archive.parrotsec.org/parrot/ rolling main contrib non-free</sub>|
|Estonia<br>cspacehosting<br>/|cspacehosting|[mirror.cspacehostings.com/parrotsec](https://mirror.cspacehostings.com/parrotsec)|<sub>deb https://mirror.cspacehostings.com/parrotsec rolling main contrib non-free</sub>|
|Russia<br>Yandex<br>1 Gbps|Yandex|[mirror.yandex.ru/mirrors/parrot](http://mirror.yandex.ru/mirrors/parrot)|<sub>deb https://mirror.yandex.ru/mirrors/parrot/ rolling main contrib non-free</sub>|
|Russia<br>Truenetwork<br>10 Gbps|Truenetwork|[mirror.truenetwork.ru/parrot](http://mirror.truenetwork.ru/parrot)|<sub>deb https://mirror.truenetwork.ru/parrot/ rolling main contrib non-free</sub>|
|Russia<br>surf<br>/|surf|[mirror.surf/parrot](https://mirror.surf/parrot)|<sub>deb https://mirror.surf/parrot rolling main contrib non-free</sub>|
|Ukraine<br>comsys<br>1 Gbps|KPI (National Technical University of Ukraine - Comsys)|[mirrors.comsys.kpi.ua/parrot](http://mirrors.comsys.kpi.ua/parrot)|<sub>only ISO files are mirrored</sub>|
|Ukraine<br>astra.in.ua<br>/|ISP|[parrot.astra.in.ua/](https://parrot.astra.in.ua/)|<sub>deb https://parrot.astra.in.ua/ rolling main contrib non-free</sub>|


### APAC ###
Asia and Pacific

| Location<br>Mirror ID<br>bandwidth| Provider Name | URL | APT config string |
|:--------------------------------------|:---------------:|:-----|:-------------------|
|Bangladesh<br>Amberit<br>1 Gbps|Amberit (formerly Dhakacom)|[mirror.amberit.com.bd/parrotsec](http://mirror.amberit.com.bd/parrotsec)|<sub>deb http://mirror.amberit.com.bd/parrotsec/ rolling main contrib non-free</sub>|
|Taiwan<br>NCHC<br>20 Gbps|NCHC (Free Software Lab)|[free.nchc.org.tw/parrot](http://free.nchc.org.tw/parrot)|<sub>deb http://free.nchc.org.tw/parrot/ rolling main contrib non-free</sub>|
|Singapore<br>0x<br>10 Gbps|0x|[mirror.0x.sg/parrot](http://mirror.0x.sg/parrot)|<sub>deb https://mirror.0x.sg/parrot/ rolling main contrib non-free</sub>|
|China<br>USTC<br>1Gbps CMCC<br>1Gbps Cernet<br>300Mbps ChinaNet|University of Science and Technology of China and USTCLUG|[mirrors.ustc.edu.cn/parrot](http://mirrors.ustc.edu.cn/parrot)|<sub>deb http://mirrors.ustc.edu.cn/parrot rolling main contrib non-free</sub>|
|China<br>TUNA<br>2 Gbps|TUNA (Tsinghua university of Beijing, TUNA association)|[mirrors.tuna.tsinghua.edu.cn/parrot](http://mirrors.tuna.tsinghua.edu.cn/parrot)|<sub>deb https://mirrors.tuna.tsinghua.edu.cn/parrot/ rolling main contrib non-free</sub>|
|China<br>SJTUG<br>2 Gbps|SJTUG (SJTU *NIX User Group)|[mirrors.sjtug.sjtu.edu.cn/parrot](http://mirrors.sjtug.sjtu.edu.cn/parrot)|<sub>deb https://mirrors.sjtug.sjtu.edu.cn/parrot/ rolling main contrib non-free</sub>|
|New Caledonia<br>Lagoon<br>1 Gbps|Lagoon Networks|[mirror.lagoon.nc/pub/parrot](http://mirror.lagoon.nc/pub/parrot)|<sub>deb http://mirror.lagoon.nc/pub/parrot/ rolling main contrib non-free</sub>|
|Thailand<br>KKU<br>1 Gbps|KKU (Khon Kaen University)|[mirror.kku.ac.th/parrot](http://mirror.kku.ac.th/parrot)|<sub>deb https://mirror.kku.ac.th/parrot/ rolling main contrib non-free</sub>|
|Indonesia<br>Datautama<br>1 Gbps|Datautama (PT. Data Utama Dinamika)|[kartolo.sby.datautama.net.id/parrot](http://kartolo.sby.datautama.net.id/parrot)|<sub>deb http://kartolo.sby.datautama.net.id/parrot/ rolling main contrib non-free</sub>|

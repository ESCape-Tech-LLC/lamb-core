# Server init guide for Ubuntu 16.04 xenial

## Update system packages
Before installation of any pservices should update all system packages and install some common used packages.

```
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install -y wget vim git zlib1g-dev openssl libssl-dev bzip2 libbz2-dev zip gcc build-essential g++ libjpeg-dev libpng-dev libtiff-dev libmagic-dev libreadline-gplv2-dev libncursesw5-dev libsqlite3-dev libgdbm-dev libc6-dev adduser libfontconfig
```

## 1. NGINX
### Add signing key
```
cd ~
wget http://nginx.org/keys/nginx_signing.key
sudo apt-key add nginx_signing.key
rm -rf nginx_signing.key
```

### Add repo
```
sudo cat <<EOF | sudo tee /etc/apt/sources.list.d/nginx.list
# NGINX ubuntu 16.04 xenial repo
deb http://nginx.org/packages/mainline/ubuntu/ xenial nginx
deb-src http://nginx.org/packages/mainline/ubuntu/ xenial nginx
EOF
```

### Install and enable NGINX
```
sudo apt-get update -y
sudo apt-get install -y nginx
sudo systemctl enable nginx
sudo systemctl restart nginx
```

### Create default site folders
```
sudo mkdir /etc/nginx/sites-available /etc/nginx/sites-enabled
```

### Update major configs
```
sudo vim /etc/nginx/nginx.conf
```

Should looks like

```
# main nginx configs
user  nginx;
worker_processes  auto;


error_log  /var/log/nginx/error.log warn;
pid        /var/run/nginx.pid;


events {
    worker_connections  1024;
}


http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for" [ $request_time sec ]';

    access_log  /var/log/nginx/access.log  main;

    sendfile            on;
    tcp_nopush          on;
    tcp_nodelay         on;
    keepalive_timeout   65;
    types_hash_max_size 2048;

    gzip            on;
    gzip_disable    "msie6";

    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*.conf;
}
```

## 2. Python
### Interpeter
Compile python from sources. For last version visit [this page] (https://www.python.org/downloads/source/)

```
cd ~
wget https://www.python.org/ftp/python/3.6.4/Python-3.6.4.tgz
tar -xzf Python-3.6.4.tgz
cd Python-3.6.4
./configure --enable-optimizations
make 
sudo male altinstall
cd ~
sudo rm -rf Python-3.6.4*
```

### Packages
Install PyPI package manager as alternatives and install Virtualenv package

```
sudo update-alternatives --install /usr/bin/pip pip /usr/local/bin/pip3.6 60
sudo pip install virtualenv
```

## 3. PostgreSQL
### Server and client
Install package and enable service. For last version visit [this page] (https://www.postgresql.org/download/linux/redhat/)

### Add signing key
```
cd ~
wget https://www.postgresql.org/media/keys/ACCC4CF8.asc
sudo apt-key add ACCC4CF8.asc
rm -rf ACCC4CF8.asc
```

### Add repo
```
sudo cat <<EOF | sudo tee /etc/apt/sources.list.d/pgsql.list
# PosqtgreSQL 10 ubuntu 16.04 xenial repo
deb http://apt.postgresql.org/pub/repos/apt/ xenial-pgdg main
EOF
```

### Install server and enable service
```
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

### Change root user password
```
# switch user to trusted psql user
sudo su postgres

# run psql cli 
psql
# recommendation - generate password with $ openssl rand -base64 10
ALTER ROLE postgres WITH PASSWORD '**********';
\q

# get out from postgres user shell
exit
```

### Allow localhost connections with password
To allow connections from localhost with password need to update pg_hba.conf file

```
# can be changed only under root/postgres user
sudo vim /etc/postgresql/10/main/pg_hba.conf
```

Auth section should looks like

```
# DO NOT DISABLE!
# If you change this first entry you will need to make sure that the
# database superuser can access the database using some other method.
# Noninteractive access to all databases is required during automatic
# maintenance (custom daily cronjobs, replication, and similar tasks).
#
# Database administrative login by Unix domain socket
local   all             postgres                                peer

# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   all             all                                     md5

# IPv4 local connections:
host    all             all             127.0.0.1/32            md5

# IPv6 local connections:
host    all             all             ::1/128                 md5

# Allow replication connections from localhost, by a user with the
# replication privilege.
local   replication     all                                     peer
host    replication     all             127.0.0.1/32            md5
host    replication     all             ::1/128                 md5
```

Restart database server to apply changes

```
sudo systemctl restart postgresql
```

## 4. RabbitMQ
For latest versions visit [this page] (https://www.rabbitmq.com/install-debian.html)

### Install Erlang
```
wget https://packages.erlang-solutions.com/erlang-solutions_1.0_all.deb
sudo dpkg -i erlang-solutions_1.0_all.deb
sudo apt-get update
sudo apt-get install -y erlang
rm -rf erlang-solutions_1.0_all.deb
```

### Add signing key
```
cd ~
wget https://dl.bintray.com/rabbitmq/Keys/rabbitmq-release-signing-key.asc
sudo apt-key add rabbitmq-release-signing-key.asc
rm -r
```

### Add repo
```
sudo cat <<EOF | sudo tee /etc/apt/sources.list.d/rabbitmq.bintray.list
# RabbitMQ ubuntu 16.04 xenial repo
deb https://dl.bintray.com/rabbitmq/debian xenial main
EOF
```

### Install RabbitMQ
```
sudo apt-get update
sudo apt-get install -y rabbitmq-server

sudo systemctl enable rabbitmq-server
sudo systemctl start rabbitmq-server
```

## 5. Telegraf / InfluxDB
### Add signing key
```
cd ~
wget https://repos.influxdata.com/influxdb.key
sudo apt-key add influxdb.key
rm -rf influxdb.key
```

### Add repo
```
source /etc/lsb-release

sudo cat <<EOF | sudo tee /etc/apt/sources.list.d/influxdb.list
# InfluxDB ubuntu 16.04 xenial repo
deb https://repos.influxdata.com/${DISTRIB_ID,,} ${DISTRIB_CODENAME} stable
EOF
```

### Install InfluxDB/Telegraf
```
sudo apt-get update
sudo apt-get install -y influxdb telegraf

sudo systemctl enable telegraf
sudo systemctl start telegraf

sudo systemctl enable influxdb
sudo systemctl start influxdb
```

### Configure telegraf inputs, bind telegraf to database output

```
# Enable rabbitmq plugin for monitoring
sudo rabbitmq-plugins enable rabbitmq_management

# Set nginx logs owner
sudo vim /etc/logrotate.d/nginx

/var/log/nginx/*.log {
        daily
        missingok
        rotate 52
        compress
        delaycompress
        notifempty
        # change to this from nginx adm:
        create 640 nginx nginx
        sharedscripts
        postrotate
                if [ -f /var/run/nginx.pid ]; then
                        kill -USR1 `cat /var/run/nginx.pid`
                fi
        endscript
        ...

sudo chown -R nginx:nginx /var/log/nginx

# Add telegraf user to nginx group, so it can read nginx logs
sudo usermod -a -G nginx telegraf

# Update telegraf config
sudo vim /etc/telegraf/telegraf.conf

## Read Nginx's basic status information (ngx_http_stub_status_module)
[[inputs.nginx]]
  urls = ["http://localhost/server-status/"]
  
## Parse Nginx's access logs
[[inputs.logparser]]
  files = ["/var/log/nginx/*access.log"]
  [inputs.logparser.grok]
    patterns = ['%{HOSTNAME:remote_addr} - %{USERNAME:remote_user} \[%{HTTPDATE:time_local}\] \"%{DATA:request}\" %{INT:status:int} %{INT:bytes_sent} \"%{DATA:http_referer}\" \"%{DATA:http_user_agent}\" \"%{DATA:http_x_forwarded_for}\" \[ %{NUMBER:request_time:float} sec \]']
    measurement = "nginx_access_log"
    
## Reads metrics from RabbitMQ servers via the Management Plugin
[[inputs.rabbitmq]]
    url = "http://localhost:15672"
    username = "guest"
    password = "guest"

## Configuration for influxdb server to send metrics to
[[outputs.influxdb]]
  ## The target database for metrics (telegraf will create it if not exists).
  database = "monitoring" 
  username = "monitoring"
  password = "<password>"
  
  
# Reload agent settings
sudo systemctl reload telegraf
```


## 6. Grafana
### Add signing key
```
cd ~
wget https://packagecloud.io/gpg.key
sudo apt-key add gpg.key
rm -rf gpg.key
```

### Add repo
```
sudo cat <<EOF | sudo tee /etc/apt/sources.list.d/grafana.list
# Grafana ubuntu 16.04 xenial repo
deb https://packagecloud.io/grafana/stable/debian/ jessie main
# do not worry about 'jessie' keyword in repo declaration - it's ok
EOF
```

### Install Grafana
```
sudo apt-get update
sudo apt-get install grafana

sudo systemctl enable grafana-server
sudo systemctl start grafana-server
```

### Change admin password
* Visit grafana dashboard at: <host>:3000
* Use default pair `admin/admin` to authorize
* Go to preferencies and change password


## 7. Memcached
```
sudo apt-get install -y memcached
sudo systemctl enable memcached
sudo systemctl restart memcached
```


# Server init guide for Centos/RHEL 7

## Update system packages
```
sudo yum update -y
sudo yum install -y wget vim git zlib zlib-devel openssl openssl-devel bzip2 bzip2-devel zip gcc gcc-c++ libjpeg-devel libpng-devel libtiff-devel file-devel policycoreutils-python
```

## 1. NGINX
### Add repo info:

```
cat <<EOF | sudo tee /etc/yum.repos.d/nginx.repo
[nginx]
name=nginx repo
baseurl=http://nginx.org/packages/mainline/centos/\$releasever/\$basearch/
gpgcheck=0
enabled=1
EOF
```

### Install and enable NGINX
```
sudo yum install -y nginx
sudo systemctl enable nginx
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

### Update Selinux configs
```
sudo setsebool httpd_can_network_connect on -P
sudo semanage permissive -a httpd_t
```

## 2. Python
### Interpeter
Compile python from sources. For last version visit: https://www.python.org/downloads/source/

```
cd ~
wget https://www.python.org/ftp/python/3.6.5/Python-3.6.5.tgz
tar -xzf Python-3.6.5.tgz
cd Python-3.6.5
./configure --enable-optimizations
make 
sudo make altinstall
cd ~
sudo rm -rf Python-3.6.5*
```

### Packages
Install PyPI package manaer as alternatives and install Virtualenv package

```
sudo alternatives --install /usr/bin/pip pip /usr/local/bin/pip3.6 60
sudo pip install virtualenv
```

## 3. PostgreSQL
### Server and client
Install package and enable service. For last version visit [Download page](https://www.postgresql.org/download/linux/redhat/)

```
sudo yum install -y https://download.postgresql.org/pub/repos/yum/10/redhat/rhel-7-x86_64/pgdg-centos10-10-2.noarch.rpm
sudo yum install -y postgresql10-server postgresql10-contrib postgresql10
sudo /usr/pgsql-10/bin/postgresql-10-setup initdb
sudo systemctl enable postgresql-10
sudo systemctl start postgresql-10
```

### Change root user password
```
# switch user to trusted psql user
sudo su postgres

# run psql cli 
psql

# add password
> ALTER USER postgres WITH PASSWORD '<password>';
> \q

# get out from postgres user shell
exit
```

### Allow localhost connections with password
To allow connections from localhost with password need to update pg_hba.conf file

```
# can be changed only under root/postgres user
sudo su
sudo vim /var/lib/pgsql/10/data/pg_hba.conf
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
# disable on production stand
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

Restart database server and leave root shell

```
sudo systemctl restart postgresql-10
exit
```
## 4. RabbitMQ
### Add erlang repo
For latest version visit [Download page](https://github.com/rabbitmq/erlang-rpm)

```
cat <<EOF | sudo tee /etc/yum.repos.d/rabbitmq-erlang.repo
[rabbitmq-erlang]
name=rabbitmq-erlang
baseurl=https://dl.bintray.com/rabbitmq/rpm/erlang/20/el/\$releasever
gpgcheck=1
gpgkey=https://dl.bintray.com/rabbitmq/Keys/rabbitmq-release-signing-key.asc
repo_gpgcheck=0
enabled=1
EOF
```

### Install erlang
```
sudo yum install -y erlang
```

### Install RabbitMQ
For latest version visit [Download page] (https://www.rabbitmq.com/install-rpm.html)

```
cd ~
wget https://dl.bintray.com/rabbitmq/all/rabbitmq-server/3.7.5/rabbitmq-server-3.7.5-1.el7.noarch.rpm
rpm --import https://www.rabbitmq.com/rabbitmq-release-signing-key.asc
sudo yum install -y rabbitmq-server-3.7.5-1.el7.noarch.rpm
sudo rm -rf rabbitmq-server-3.7.5-1.el7.noarch.rpm
```

### Register and start daemon
```
sudo systemctl enable rabbitmq-server
sudo systemctl start rabbitmq-server
```

## 5. Telegraf/InfluxDB
### Add yum repo
```
cat <<EOF | sudo tee /etc/yum.repos.d/influxdb.repo
[influxdb]
name = InfluxDB Repository - RHEL \$releasever
baseurl = https://repos.influxdata.com/rhel/\$releasever/\$basearch/stable
enabled = 1
gpgcheck = 1
gpgkey = https://repos.influxdata.com/influxdb.key
EOF
```

### Install and start services
```
sudo yum install -y telegraf influxdb

sudo systemctl enable telegraf
sudo systemctl start telegraf

sudo systemctl enable influxdb
sudo systemctl start influxdb
```

### Enable authentication on InfluxDB 
```
sudo vim /etc/influxdb/influxdb.conf
```
Need to change `http` section field `auth-enabled`

```
[http]
  # Determines whether user authentication is enabled over HTTP/HTTPS.
  auth-enabled = true
```

Restart service to apply changes

```
sudo systemctl restart influxdb
```

### Create InfluxDB users / databases
Start InfluxDB shell and inside InfluxDB CLI created two users and database

```
influx

CREATE USER monitoring WITH PASSWORD '<password>';
CREATE USER admin WITH PASSWORD '<password>' WITH ALL PRIVILEGES;
CREATE DATABASE monitoring;
GRANT ALL ON monitoring TO monitoring;
quit
```

Configure telegraf inputs, bind telegraf to new created database output

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
```


## 6. Grafana
### Add yum repo
```
cat <<EOF | sudo tee /etc/yum.repos.d/grafana.repo
[grafana]
name=grafana
baseurl=https://packagecloud.io/grafana/stable/el/6/\$basearch
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://packagecloud.io/gpg.key https://grafanarel.s3.amazonaws.com/RPM-GPG-KEY-grafana
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
EOF
```


### Install Grafana
```
sudo yum install -y grafana

sudo systemctl enable grafana-server
sudo systemctl start grafana-server
```

### Open port 3000
Grafana by default start on port 3000, if you would not run it under http-proxy - you need to enable port 3000.

```
firewall-cmd --zone=public --add-port=3000/tcp --permanent
firewall-cmd --reload
```

### Update grafana configs
To finish configuration please, visit grafana on port 3000:

* Change admin credential pair in user preferences (default `admin/admin`)
* Create new user if required
* Config grafana to use influxdb as data source
* Import dashboards and config it

## 7. Memcached
```
sudo yum install -y memcached
sudo systemctl enable memcached
sudo systemctl restart memcached
```

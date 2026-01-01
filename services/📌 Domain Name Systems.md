# DNS (Domain Name Resolution)
Promox LXC Service Deployment Manual

# Proxmox LXC Service HA Deployment Template
> For stateful services (DNS, DBs, etc.) with multi-node replication

## 1️⃣ Global Service Configuration (All Nodes)
*Applies identically to DNS-01, DNS-02, DNS-03 unless overridden*

| Category         | Setting               | Value/Example       | Description                     |
|------------------|-----------------------|---------------------|---------------------------------|
| **Proxmox**      | Resource Pool         | `DNS-Pool`          | Logical group for HA management |
|                  | Storage               | `ceph-dns`          | Replicated CephFS volume        |
| **LXC**          | OS Template           | `ubuntu-22.04-dns`  | Preconfigured image             |
|                  | CPU Cores             | 2                   | Guaranteed cores                |
|                  | Memory                | 1024MB              | Minimum RAM allocation          |
| **Network**      | Bridge                | `vmbr1`             | Private HA network              |
|                  | VLAN Tag              | 110                 | Isolated service VLAN           |
| **DNS Service**  | Software              | `bind9`             | DNS server package              |
|                  | Config Dir            | `/etc/bind`         | Bind configuration path         |
|                  | Zone Refresh          | 3600                | Secondary sync interval (sec)   |

---

## 2️⃣ Node-Specific Configuration
*Unique values per instance - replace bracketed placeholders*

| Node     | Setting          | Value             | Override Reason          |
|----------|------------------|-------------------|--------------------------|
| **DNS-01** | IP Address       | `192.168.110.11`  | Primary master           |
|          | Proxmox Host     | `pve-node-03`     | Initial deployment host  |
|          | `named.conf` Role| `master`          | Zone file authority      |
| **DNS-02** | IP Address       | `192.168.110.12`  | Secondary                |
|          | Proxmox Host     | `pve-node-07`     | Spread across racks      |
|          | `named.conf` Role| `slave`           | Auto sync from master    |
| **DNS-03** | IP Address       | `192.168.110.13`  | Secondary                |
|          | CPU Cores        | 4                 | Higher query load        |
|          | `named.conf` Role| `slave`           | Auto sync from master    |

---

## 3️⃣ Proxmox Deployment Workflow
### Step 1: Clone Base LXC Template
```bash
# Create DNS instances from template (ID 9000)
for NODE in 01 02 03; do
  pct clone 9000 11${NODE} \
    --hostname DNS-${NODE} \
    --storage ceph-dns \
    --pool DNS-Pool
done
```
```
## Common Settings

||DNS-01|DNS-02|
|-|-|-|
|Networking|||||
||k|k|k|k|

### Network
|Attrib|Value  |
|----|-------|
|Bridge|vmbr0|
|IPv4 Address|10.1.1.1/8|
|IPv4 Gateway|10.0.0.1|
|IPv6 Address|2a0e:1d47:da88:8f00::1:1:1/64|
|IPv6 Gateway|2a0e:1d47:da88:8f00::|

### Operating System
|Attrib|Value  |
|----|-------|
|OS|Alpine|
|Type|LXC|

### Options
|Attrib|Value  |
|----|-------|
|Start At Boot|Yes|
|Protection|Yes|
|Unprivileged Container|Yes|


### Resources
|Attrib|Value|
|----|-------|
|Cores|1|
|Drive|8 GiB|
|Memory|512 M1B|
|Swap|512 M1B|

## Installation

1. Ensure we are running latest updates and security patches

```sh
apk update
apk upgrade
```

2. Install all required packages

```sh
apk add mariadb mariadb-client pdns pdns-backend-mariadb
```

3. Install and secure database

```sh
mariadb-install-db
mariadb-secure-installation
```

Enable unix_socket authentication?: Y<br />
Change the root password?: Y<br />
Remove the anonymous users?: Y<br />
Disallow root login remotely? Y<br />
Remove test database and access to it?: Y<br />
Reload privileges tables now? Y

4. Initlaise Database

```sh
/etc/init.d/mariadb setup
```

5. Start and verifiy database status

```sh
rc-update add mariadb
rc-service mariadb start
rc-service mariadb status
```

6. Setup database and user for PowerDNS

```sh
mariadb -u root <<EOF
    CREATE DATABASE powerdns;
    CREATE USER IF NOT EXISTS 'pdns'@'localhost' IDENTIFIED BY 'p0w3rdn5';
    CREATE USER IF NOT EXISTS 'pdns'@'127.0.0.1' IDENTIFIED BY 'p0w3rdn5';
    CREATE USER IF NOT EXISTS 'pdns'@'::1' IDENTIFIED BY 'p0w3rdn5';
    CREATE USER IF NOT EXISTS 'pdns'@'%' IDENTIFIED BY 'p0w3rdn5';
    GRANT ALL PRIVILEGES ON powerdns.* TO 'pdns'@'localhost';
    GRANT ALL PRIVILEGES ON powerdns.* TO 'pdns'@'127.0.0.1';
    GRANT ALL PRIVILEGES ON powerdns.* TO 'pdns'@'::1';
    GRANT ALL PRIVILEGES ON powerdns.* TO 'pdns'@'%';
    FLUSH PRIVILEGES;
EOF
```

7. Import PowerDNS schema

Copy and import the schema from the bottom of this [PowerDNS](https://doc.powerdns.com/authoritative/backends/generic-mysql.html) location. As of version 4.7 the command looks as follows:

```sh
mariadb -u root powerdns <<EOF
    CREATE TABLE domains (
        id                    INT AUTO_INCREMENT,
        name                  VARCHAR(255) NOT NULL,
        master                VARCHAR(128) DEFAULT NULL,
        last_check            INT DEFAULT NULL,
        type                  VARCHAR(8) NOT NULL,
        notified_serial       INT UNSIGNED DEFAULT NULL,
        account               VARCHAR(40) CHARACTER SET 'utf8' DEFAULT NULL,
        options               VARCHAR(64000) DEFAULT NULL,
        catalog               VARCHAR(255) DEFAULT NULL,
        PRIMARY KEY (id)
    ) Engine=InnoDB CHARACTER SET 'latin1';

    CREATE UNIQUE INDEX name_index ON domains(name);
    CREATE INDEX catalog_idx ON domains(catalog);


    CREATE TABLE records (
        id                    BIGINT AUTO_INCREMENT,
        domain_id             INT DEFAULT NULL,
        name                  VARCHAR(255) DEFAULT NULL,
        type                  VARCHAR(10) DEFAULT NULL,
        content               VARCHAR(64000) DEFAULT NULL,
        ttl                   INT DEFAULT NULL,
        prio                  INT DEFAULT NULL,
        disabled              TINYINT(1) DEFAULT 0,
        ordername             VARCHAR(255) BINARY DEFAULT NULL,
        auth                  TINYINT(1) DEFAULT 1,
        PRIMARY KEY (id)
    ) Engine=InnoDB CHARACTER SET 'latin1';

    CREATE INDEX nametype_index ON records(name,type);
    CREATE INDEX domain_id ON records(domain_id);
    CREATE INDEX ordername ON records (ordername);


    CREATE TABLE supermasters (
        ip                    VARCHAR(64) NOT NULL,
        nameserver            VARCHAR(255) NOT NULL,
        account               VARCHAR(40) CHARACTER SET 'utf8' NOT NULL,
        PRIMARY KEY (ip, nameserver)
    ) Engine=InnoDB CHARACTER SET 'latin1';


    CREATE TABLE comments (
        id                    INT AUTO_INCREMENT,
        domain_id             INT NOT NULL,
        name                  VARCHAR(255) NOT NULL,
        type                  VARCHAR(10) NOT NULL,
        modified_at           INT NOT NULL,
        account               VARCHAR(40) CHARACTER SET 'utf8' DEFAULT NULL,
        comment               TEXT CHARACTER SET 'utf8' NOT NULL,
        PRIMARY KEY (id)
    ) Engine=InnoDB CHARACTER SET 'latin1';

    CREATE INDEX comments_name_type_idx ON comments (name, type);
    CREATE INDEX comments_order_idx ON comments (domain_id, modified_at);


    CREATE TABLE domainmetadata (
        id                    INT AUTO_INCREMENT,
        domain_id             INT NOT NULL,
        kind                  VARCHAR(32),
        content               TEXT,
        PRIMARY KEY (id)
    ) Engine=InnoDB CHARACTER SET 'latin1';

    CREATE INDEX domainmetadata_idx ON domainmetadata (domain_id, kind);


    CREATE TABLE cryptokeys (
        id                    INT AUTO_INCREMENT,
        domain_id             INT NOT NULL,
        flags                 INT NOT NULL,
        active                BOOL,
        published             BOOL DEFAULT 1,
        content               TEXT,
        PRIMARY KEY(id)
    ) Engine=InnoDB CHARACTER SET 'latin1';

    CREATE INDEX domainidindex ON cryptokeys(domain_id);


    CREATE TABLE tsigkeys (
        id                    INT AUTO_INCREMENT,
        name                  VARCHAR(255),
        algorithm             VARCHAR(50),
        secret                VARCHAR(255),
        PRIMARY KEY (id)
    ) Engine=InnoDB CHARACTER SET 'latin1';

    CREATE UNIQUE INDEX namealgoindex ON tsigkeys(name, algorithm);
EOF
```

8. Configure some basic settings for PowerDNS

PowerDNS is a very advanced name server and supports everything you could want. For our purposes right now, we are simply going to enable the Authoritative Name Server, Web Server and API.

```sh
mkdir /etc/pdns/pdns.d

cat <<EOF >> /etc/pdns/pdns.conf
include-dir=/etc/pdns/pdns.d
EOF

cat <<EOF > /etc/pdns/pdns.d/api.conf
api=yes
api-key=secret-api-key
EOF

cat <<EOF > /etc/pdns/pdns.d/launch.conf
launch=gmysql
EOF

cat <<EOF > /etc/pdns/pdns.d/mysql.conf 
gmysql-host=localhost
gmysql-dbname=powerdns
gmysql-user=pdns
gmysql-password=p0w3rdn5
EOF

cat <<EOF > /etc/pdns/pdns.d/webserver.conf
webserver=yes
webserver-address=10.1.1.1
webserver-allow-from=10.0.0.0/8,2a0e:1d47:da88:8f00::/64,::1/128
webserver-password=secret
webserver-port=8081
EOF
```

9. Start PowerDNS service and check status

```sh
rc-update add pdns
rc-service pdns start
rc-service pdns status
```

10. Time to add our first zone

To configure our base zone, we'll use the `pdnsutil` utility.

First off, lets create our zone for the `andronics.io` domain.

```sh
pdnsutil create-zone "andronics.io"
```
Next, we will register as `NS` record to identify our  nameservers for this domain.

```sh
pdnsutil add-record andronics.io @ NS 10.1.1.1
```

Now add some new hosts records `A`,`AAAA` and `CNAME`which we can use to test resolution.

```sh
pdnsutil add-record andronics.io dns-01 A 10.1.1.1
pdnsutil add-record andronics.io node-01 A 10.0.0.11
pdnsutil add-record andronics.io node-02 A 10.0.0.12
pdnsutil add-record andronics.io node-03 A 10.0.0.13
```
